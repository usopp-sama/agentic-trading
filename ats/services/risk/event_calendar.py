"""Event-risk veto gate: "is this a stupid moment to add exposure?"

The one "news" component in the fast loop, and it is deterministic + LLM-free:

- **Calendar vetoes (pure data):** a maintained YAML of dated events — RBI MPC
  days, Union Budget day, index-rebalancing dates (global), and per-symbol
  earnings dates. A symbol event within ±1 day vetoes that name; a global
  event vetoes everything. F&O monthly expiry (last Thursday) is computed.
- **Severity flag (local NLP):** an extreme negative sentiment burst on a
  name (from the existing FinBERT/VADER scores — no LLM call) sets a
  one-session entry veto for it.
- **Manual veto:** per-symbol or global, flipped from the dashboard/API when
  the operator knows something is off.

Semantics (enforced by the callers — RiskService and the league): vetoes
block NEW entries only. Exits and risk-reducing orders always pass. Every
veto that fires is recorded on the decision's rules_applied, so the audit
chain shows why nothing traded.

Calendar file format (``ATS_EVENT_CALENDAR_PATH``, YAML)::

    global:
      - {date: 2026-08-06, kind: rbi_mpc, note: MPC decision}
      - {date: 2027-02-01, kind: union_budget}
      - {date: 2026-09-25, kind: index_rebalance}
    symbols:
      RELIANCE.NS:
        - {date: 2026-07-18, kind: earnings}
"""

from __future__ import annotations

import time
from collections import deque
from datetime import date, timedelta
from pathlib import Path

from ats.core import state
from ats.core.config import get_settings
from ats.core.events import Topic
from ats.core.logging import get_logger

log = get_logger("ats.event_risk")

_MANUAL_KEY = "veto:manual"
_SEVERITY_KEY = "veto:severity"


def _as_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def surprise_pct(actual: float | None, estimate: float | None) -> float | None:
    """The calendar "surprise": ``(actual - estimate) / |estimate| * 100``.

    Markets react to the surprise, not the absolute print. ``None`` when either
    input is missing or the estimate is zero (surprise is undefined)."""
    if actual is None or estimate is None or estimate == 0:
        return None
    return (actual - estimate) / abs(estimate) * 100.0


def last_thursday(year: int, month: int) -> date:
    """NSE F&O monthly expiry day (holiday shifts not modeled — close enough
    for a veto that errs on the side of caution)."""
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    d = nxt - timedelta(days=1)
    while d.weekday() != 3:  # Thursday
        d -= timedelta(days=1)
    return d


class EventCalendar:
    """The maintained YAML of dated event vetoes."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or get_settings().event_calendar_path)
        self._global: list[dict] = []
        self._symbols: dict[str, list[dict]] = {}
        self.reload()

    def reload(self) -> None:
        self._global, self._symbols = [], {}
        if not self.path.exists():
            return
        try:
            import yaml

            raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001 — a bad file must not kill risk
            log.warning("event_calendar_load_failed", extra={"error": str(exc)})
            return
        self._global = [self._norm(e) for e in raw.get("global", []) or []]
        for sym, events in (raw.get("symbols", {}) or {}).items():
            self._symbols[str(sym)] = [self._norm(e) for e in events or []]

    @staticmethod
    def _norm(e: dict) -> dict:
        d = e.get("date")
        if isinstance(d, str):
            d = date.fromisoformat(d)
        est = _as_float(e.get("estimate"))
        act = _as_float(e.get("actual"))
        out = {"date": d, "kind": str(e.get("kind", "event")),
               "note": str(e.get("note", "")), "estimate": est, "actual": act}
        sp = surprise_pct(act, est)
        if sp is not None:
            out["surprise_pct"] = round(sp, 2)
        return out

    def global_events(self, on: date) -> list[dict]:
        return [e for e in self._global if e["date"] == on]

    def symbol_events(self, symbol: str, on: date, window_days: int = 1) -> list[dict]:
        out = []
        for e in self._symbols.get(symbol, []):
            if e["date"] is not None and abs((e["date"] - on).days) <= window_days:
                out.append(e)
        return out


class EventRiskService:
    """Bus-wired veto oracle. RiskService and the league consult
    ``active_vetoes(symbol)`` before allowing any exposure increase."""

    name = "event_risk"

    def __init__(self, calendar: EventCalendar | None = None) -> None:
        self.calendar = calendar or EventCalendar()
        # symbol -> deque[(epoch, score)] for the severity burst detector
        self._sent: dict[str, deque] = {}

    async def start(self, ctx) -> None:
        ctx.bus.subscribe(Topic.SENTIMENT, self._on_sentiment)
        log.info("event_risk_started",
                 extra={"calendar": str(self.calendar.path),
                        "has_file": self.calendar.path.exists()})

    # --- severity flag (local NLP; no LLM) -----------------------------------
    async def _on_sentiment(self, evt) -> None:
        self.observe_sentiment(evt.payload)

    def observe_sentiment(self, payload: dict) -> None:
        score = float(payload.get("score", 0.0) or 0.0)
        settings = get_settings()
        now = time.time()
        window_s = settings.severity_veto_window_min * 60
        for symbol in payload.get("tickers", []) or []:
            dq = self._sent.setdefault(symbol, deque(maxlen=50))
            dq.append((now, score))
            recent = [s for ts, s in dq if now - ts <= window_s]
            if (
                len(recent) >= settings.severity_veto_min_count
                and sum(recent) / len(recent) <= settings.severity_veto_score
            ):
                self._set_severity_veto(symbol, sum(recent) / len(recent))

    def _set_severity_veto(self, symbol: str, mean_score: float) -> None:
        vetoes = state.get_kv(_SEVERITY_KEY)
        today = date.today().isoformat()
        if vetoes.get(symbol) == today:
            return  # already flagged this session
        vetoes[symbol] = today
        state.set_kv(_SEVERITY_KEY, vetoes)
        log.warning("severity_veto_set",
                    extra={"symbol": symbol, "mean_score": round(mean_score, 3)})
        state.audit("event_risk", "veto.severity",
                    {"symbol": symbol, "mean_score": round(mean_score, 3)})

    # --- manual veto ------------------------------------------------------------
    def set_manual_veto(self, symbol: str | None, engaged: bool,
                        actor: str = "human", reason: str = "") -> dict:
        manual = state.get_kv(_MANUAL_KEY, {"global": False, "symbols": {}})
        if symbol is None:
            manual["global"] = engaged
        else:
            symbols = dict(manual.get("symbols", {}))
            if engaged:
                symbols[symbol] = reason or "manual"
            else:
                symbols.pop(symbol, None)
            manual["symbols"] = symbols
        state.set_kv(_MANUAL_KEY, manual)
        state.audit(actor, "veto.manual",
                    {"symbol": symbol, "engaged": engaged, "reason": reason})
        return manual

    # --- the gate ------------------------------------------------------------------
    def active_vetoes(self, symbol: str, on: date | None = None) -> list[str]:
        """Reasons this symbol must not gain exposure right now (empty = clear)."""
        on = on or date.today()
        settings = get_settings()
        reasons: list[str] = []
        for e in self.calendar.global_events(on):
            reasons.append(e["kind"])
        for e in self.calendar.symbol_events(symbol, on):
            reasons.append(f"{e['kind']}_window")
        if settings.veto_fo_expiry and on == last_thursday(on.year, on.month):
            reasons.append("fo_expiry")
        severity = state.get_kv(_SEVERITY_KEY)
        if severity.get(symbol) == on.isoformat():
            reasons.append("severity")
        manual = state.get_kv(_MANUAL_KEY, {"global": False, "symbols": {}})
        if manual.get("global"):
            reasons.append("manual_global")
        if symbol in (manual.get("symbols") or {}):
            reasons.append("manual")
        # Flow-anomaly veto (hypothesis #1): enforced only in active mode;
        # shadow entries are visible in status() but never block.
        if settings.flows_veto_mode == "active":
            flow = (state.get_kv("veto:flow") or {}).get(symbol)
            if flow and flow.get("day") == on.isoformat() and not flow.get("shadow"):
                reasons.append("flow_anomaly")
        return reasons

    def status(self) -> dict:
        """For the dashboard: everything currently vetoed and why."""
        manual = state.get_kv(_MANUAL_KEY, {"global": False, "symbols": {}})
        severity = state.get_kv(_SEVERITY_KEY)
        today = date.today()
        return {
            "today": today.isoformat(),
            "global_events": self.calendar.global_events(today),
            "fo_expiry": get_settings().veto_fo_expiry
            and today == last_thursday(today.year, today.month),
            "manual": manual,
            "severity": {s: d for s, d in severity.items()
                         if d == today.isoformat()},
            "flow": {
                "mode": get_settings().flows_veto_mode,
                "vetoes": {s: v for s, v in (state.get_kv("veto:flow") or {}).items()
                           if v.get("day") == today.isoformat()},
            },
        }
