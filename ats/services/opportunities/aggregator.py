"""Opportunity aggregator.

Joins the most recent non-neutral strategy ``Signal``, the latest ``SmeOpinion``
per expert, and the latest ``Decision`` for each symbol into a single ranked,
*scored* opportunity with a plain-English thesis. It reads primarily from the
DB (so it is testable without a running orchestrator) and enriches with live
price + per-strategy track record (sleeve stats) when an orchestrator is given.

Nothing here fabricates numbers: conviction/score come from real signals and
opinions; the per-strategy track record is the sleeve's rolling Sharpe + virtual
equity (``None`` when unknown). The "invalidation" level is clearly labelled a
heuristic derived from the last price.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Decision, Ohlcv, Signal, SmeOpinion

log = get_logger("ats.opportunities")

# How a stance maps to a direction (+1 long / -1 short / 0 neutral).
_DIR = {
    "buy": 1, "long": 1, "bullish": 1, "accumulate": 1, "overweight": 1,
    "sell": -1, "short": -1, "bearish": -1, "reduce": -1, "underweight": -1,
    "neutral": 0, "hold": 0, "flat": 0, "": 0,
}
_LOOKBACK_DAYS = 5
_INVALIDATION_PCT = 0.05  # heuristic adverse move that would void the setup


def _dir(stance) -> int:
    return _DIR.get(str(stance or "").lower(), 0)


def _conv_label(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "medium"
    return "low"


def _dir_word(d: int) -> str:
    return "bullish" if d > 0 else "bearish" if d < 0 else "neutral"


# Map jargon (strategy names / rationale keywords) to a plain-English driver.
_DRIVER_KEYWORDS = [
    (("momentum", "trend", "breakout", "sma_cross", "ts_momentum"), "price momentum"),
    (("mean_reversion", "rsi", "reversion", "oversold", "overbought"), "a mean-reversion setup"),
    (("value", "valuation", "pe", "pb", "cheap"), "valuation"),
    (("sentiment", "news"), "news & sentiment"),
    (("volume",), "a volume surge"),
    (("macro", "regime", "policy", "rate"), "the macro backdrop"),
    (("supply_chain", "peer"), "peer / supply-chain read"),
]


def _humanize_driver(lead_strat: dict | None, lead_op: dict | None) -> str:
    """One plain phrase for *why* — derived from the lead contributor."""
    hay = ""
    if lead_strat:
        hay += f" {lead_strat.get('strategy', '')}"
    if lead_op:
        hay += f" {lead_op.get('sme', '')} {lead_op.get('rationale', '')}"
    hay = hay.lower()
    for keys, phrase in _DRIVER_KEYWORDS:
        if any(k in hay for k in keys):
            return phrase
    return "multiple signals"


def _last_close(symbol: str) -> float | None:
    with session_scope() as s:
        row = s.execute(
            select(Ohlcv.close).where(Ohlcv.symbol == symbol).order_by(Ohlcv.ts.desc()).limit(1)
        ).scalar_one_or_none()
        return float(row) if row is not None else None


def _gather(now: datetime) -> tuple[dict, dict, dict]:
    """Latest non-neutral signal per (symbol, strategy), latest opinion per
    (symbol, sme), and the latest decision per symbol — all within lookback."""
    cutoff = now - timedelta(days=_LOOKBACK_DAYS)
    signals: dict[str, dict] = {}
    opinions: dict[str, dict] = {}
    decisions: dict[str, dict] = {}
    with session_scope() as s:
        for sg in s.execute(
            select(Signal).where(Signal.ts >= cutoff).order_by(Signal.id.desc()).limit(2000)
        ).scalars().all():
            key = f"{sg.symbol}\x00{sg.strategy}"
            if key in signals or _dir(sg.stance) == 0:
                continue
            signals[key] = {
                "symbol": sg.symbol, "strategy": sg.strategy, "stance": sg.stance,
                "conviction": float(sg.conviction or 0.0), "features": sg.features or {},
                "ts": sg.ts.isoformat() if sg.ts else None,
            }
        for o in s.execute(
            select(SmeOpinion).where(SmeOpinion.ts >= cutoff).order_by(SmeOpinion.id.desc()).limit(2000)
        ).scalars().all():
            key = f"{o.symbol}\x00{o.sme}"
            if key in opinions or _dir(o.stance) == 0:
                continue
            opinions[key] = {
                "symbol": o.symbol, "sme": o.sme, "stance": o.stance,
                "conviction": float(o.conviction or 0.0), "rationale": o.rationale or "",
                "key_risks": list(o.key_risks or []), "horizon": o.horizon or "",
                "ts": o.ts.isoformat() if o.ts else None,
            }
        for d in s.execute(
            select(Decision).order_by(Decision.id.desc()).limit(400)
        ).scalars().all():
            if d.symbol in decisions:
                continue
            decisions[d.symbol] = {
                "action": d.action, "qty": d.target_qty, "status": d.status,
                "rationale": d.rationale or "", "contributors": d.contributors or {},
                "ts": d.ts.isoformat() if d.ts else None,
            }
    return signals, opinions, decisions


def _status_of(decision: dict | None) -> str:
    if not decision:
        return "idea"
    st = str(decision.get("status", "")).upper()
    if "FILL" in st or st == "EXECUTED" or st == "DONE":
        return "acted"
    if "PROPOS" in st or "PENDING" in st or "APPROV" in st:
        return "proposed"
    if "BLOCK" in st or "REJECT" in st or "SKIP" in st:
        return "blocked"
    return "proposed"


def _sleeve_track(orch) -> dict:
    if not orch:
        return {}
    strat = orch.get("strategies")
    if not strat or not hasattr(strat, "sleeve_stats"):
        return {}
    try:
        return {s["strategy"]: s for s in strat.sleeve_stats()}
    except Exception as exc:  # noqa: BLE001
        log.warning("sleeve_stats_failed", extra={"error": str(exc)})
        return {}


def _price_of(orch, symbol: str) -> float | None:
    if orch:
        md = orch.get("market_data")
        if md and hasattr(md, "latest_price"):
            try:
                px = md.latest_price(symbol)
                if px:
                    return float(px)
            except Exception:  # noqa: BLE001
                pass
    return _last_close(symbol)


def _assemble(symbol, sigs, ops, decision, track, price) -> dict:
    contributors = []
    vote = 0.0
    agree_conv_sig: list[float] = []
    agree_conv_op: list[float] = []
    for sg in sigs:
        d = _dir(sg["stance"])
        vote += d * sg["conviction"]
        contributors.append({"kind": "strategy", "name": sg["strategy"],
                             "stance": sg["stance"], "conviction": round(sg["conviction"], 3)})
    for o in ops:
        d = _dir(o["stance"])
        vote += d * o["conviction"]
        contributors.append({"kind": "sme", "name": o["sme"], "stance": o["stance"],
                             "conviction": round(o["conviction"], 3)})
    net = 1 if vote > 0 else -1 if vote < 0 else 0
    for sg in sigs:
        if _dir(sg["stance"]) == net:
            agree_conv_sig.append(sg["conviction"])
    for o in ops:
        if _dir(o["stance"]) == net:
            agree_conv_op.append(o["conviction"])
    sig_strength = sum(agree_conv_sig) / len(agree_conv_sig) if agree_conv_sig else 0.0
    opi_strength = sum(agree_conv_op) / len(agree_conv_op) if agree_conv_op else 0.0
    total = len(sigs) + len(ops)
    agree = (len(agree_conv_sig) + len(agree_conv_op)) / total if total else 0.0
    score = min(1.0, 0.35 * sig_strength + 0.35 * opi_strength + 0.30 * agree)

    # lead contributor = highest-conviction agreeing item
    lead_strat = max((s for s in sigs if _dir(s["stance"]) == net),
                     key=lambda s: s["conviction"], default=None)
    lead_op = max((o for o in ops if _dir(o["stance"]) == net),
                  key=lambda o: o["conviction"], default=None)

    setup = "—"
    track_rec = None
    if lead_strat:
        setup = f"{lead_strat['strategy']} · {_dir_word(net)}"
        tr = track.get(lead_strat["strategy"])
        if tr:
            track_rec = {"strategy": lead_strat["strategy"], "sharpe": tr.get("sharpe"),
                         "equity": tr.get("equity"), "days": tr.get("days")}
    elif lead_op:
        setup = f"{lead_op['sme']} · {_dir_word(net)}"

    risks: list[str] = []
    for o in ops:
        for r in o.get("key_risks", []):
            if r and r not in risks:
                risks.append(r)

    invalidation = None
    if price:
        if net > 0:
            lvl = round(price * (1 - _INVALIDATION_PCT), 2)
            invalidation = {"level": lvl, "note": f"thesis weakens below ~{lvl} (heuristic −{int(_INVALIDATION_PCT*100)}%)"}
        elif net < 0:
            lvl = round(price * (1 + _INVALIDATION_PCT), 2)
            invalidation = {"level": lvl, "note": f"thesis weakens above ~{lvl} (heuristic +{int(_INVALIDATION_PCT*100)}%)"}

    # plain-English thesis (templated; no fabricated numbers)
    parts = []
    n_sig, n_op = len(sigs), len(ops)
    bits = []
    if n_sig:
        bits.append(f"{n_sig} strateg{'y' if n_sig==1 else 'ies'}")
    if n_op:
        bits.append(f"{n_op} expert view{'s' if n_op>1 else ''}")
    parts.append(f"{' and '.join(bits) or 'Signals'} lean {_dir_word(net)} on {symbol}.")
    if lead_strat:
        parts.append(f"Lead signal: {lead_strat['strategy']} ({lead_strat['stance']}, conviction {round(lead_strat['conviction'],2)}).")
    if lead_op and lead_op.get("rationale"):
        rat = lead_op["rationale"].strip().split("\n")[0][:200]
        parts.append(f"{lead_op['sme']}: {rat}")
    thesis = " ".join(parts)

    # Simple, plain-English summary for the card (detail keeps the full thesis).
    n_agree = len(agree_conv_sig) + len(agree_conv_op)
    voices = "expert" if (n_op and not n_sig) else "signal"
    plural = "" if n_agree == 1 else "s"
    headline = f"{n_agree} {voices}{plural} lean {_dir_word(net)}"
    driver = _humanize_driver(lead_strat, lead_op)

    return {
        "symbol": symbol,
        "direction": _dir_word(net),
        "side": "LONG" if net > 0 else "SHORT" if net < 0 else "FLAT",
        "score": round(score, 4),
        "conviction": _conv_label(score),
        "setup": setup,
        "headline": headline,
        "driver": driver,
        "strategy": lead_strat["strategy"] if lead_strat else (lead_op["sme"] if lead_op else None),
        "thesis": thesis,
        "risks": risks[:5],
        "invalidation": invalidation,
        "track_record": track_rec,
        "status": _status_of(decision),
        "price": price,
        "n_signals": n_sig,
        "n_opinions": n_op,
        "contributors": sorted(contributors, key=lambda c: c["conviction"], reverse=True),
        "updated": max([t for t in ([s.get("ts") for s in sigs] + [o.get("ts") for o in ops]) if t], default=None),
    }


def build_opportunities(orch=None, limit: int = 20, min_score: float = 0.0) -> list[dict]:
    """Ranked list of opportunities. Safe to call with ``orch=None`` (DB only)."""
    now = datetime.now(timezone.utc)
    signals, opinions, decisions = _gather(now)
    symbols = {v["symbol"] for v in signals.values()} | {v["symbol"] for v in opinions.values()}
    track = _sleeve_track(orch)
    out: list[dict] = []
    for sym in symbols:
        sigs = [v for v in signals.values() if v["symbol"] == sym]
        ops = [v for v in opinions.values() if v["symbol"] == sym]
        opp = _assemble(sym, sigs, ops, decisions.get(sym), track, _price_of(orch, sym))
        if opp["score"] >= min_score and opp["side"] != "FLAT":
            out.append(opp)
    out.sort(key=lambda o: o["score"], reverse=True)
    return out[: max(1, min(limit, 100))]


def opportunity_detail(orch, symbol: str) -> dict | None:
    """Full detail for one symbol: the opportunity + its raw contributors."""
    now = datetime.now(timezone.utc)
    signals, opinions, decisions = _gather(now)
    sigs = [v for v in signals.values() if v["symbol"] == symbol]
    ops = [v for v in opinions.values() if v["symbol"] == symbol]
    if not sigs and not ops:
        return None
    track = _sleeve_track(orch)
    opp = _assemble(symbol, sigs, ops, decisions.get(symbol), track, _price_of(orch, symbol))
    opp["signals"] = sorted(sigs, key=lambda s: s["conviction"], reverse=True)
    opp["opinions"] = sorted(ops, key=lambda o: o["conviction"], reverse=True)
    opp["decision"] = decisions.get(symbol)
    return opp
