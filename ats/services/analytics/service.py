"""AnalyticsService — per-symbol analytics snapshots, movers, and screens.

Two cadences, both cheap and both off the order path:
- **Close pass** (15:50 IST + on start): compute the full analytics snapshot
  for every watchlist symbol from stored history and persist one
  ``AnalyticsSnapshot`` row per (symbol, day). The dashboard reads these back
  instantly — page loads never trigger recomputation (QA-10 RAM rule).
- **Poll pass** (every minute, in-memory only): recompute movers + VWAP from
  the latest bars.

All heavy math is the pure ``quant.analysis`` modules; this service only wires
data in and persists results out. Nothing here proposes a trade.
"""

from __future__ import annotations

import asyncio
from datetime import date

import pandas as pd
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import AnalyticsSnapshot
from quant.analysis import intraday, patterns
from quant.analysis.levels import classic_pivots, fibonacci_retracements, session_anchor
from quant.analysis.summary import technical_summary

log = get_logger("ats.analytics")

# Screener presets: (name -> filter predicate over a metrics row dict). Config-
# free constants; custom filters can still be passed to ``screener``.
_PRESETS = {
    "value": lambda r: _le(r.get("pe"), 15) and _ge(r.get("mos_pct"), 20),
    "quality": lambda r: _ge(r.get("f_score"), 7),
    "dividend": lambda r: _ge(r.get("dividend_yield"), 0.04) and _ge(r.get("f_score"), 7),
    "momentum": lambda r: _ge(r.get("tech_score"), 3) and _ge(r.get("near_high_pct"), -5),
    # Fair-value verdicts (P1.3): the undervalued/overvalued surface.
    "undervalued": lambda r: r.get("verdict") == "undervalued",
    "overvalued": lambda r: r.get("verdict") == "overvalued",
}


def _ge(v, t) -> bool:
    return v is not None and v >= t


def _le(v, t) -> bool:
    return v is not None and v <= t


class AnalyticsService:
    name = "analytics"

    def __init__(self) -> None:
        self._md = None
        self._orch = None
        self._boot_task: asyncio.Task | None = None
        self._movers: dict = {"gainers": [], "losers": [], "volume_confirmed": []}

    async def start(self, ctx) -> None:
        self._md = ctx.orchestrator.get("market_data")
        self._orch = ctx.orchestrator

        # P0.5: the boot close-pass (52-symbol compute) used to block startup on
        # the loop. Run it off the boot path in a worker thread so the server
        # starts listening immediately; snapshots fill in a beat later.
        async def _boot_pass() -> None:
            try:
                await asyncio.to_thread(self.run_close_pass)
            except Exception as exc:  # noqa: BLE001 — boot must not fail on analytics
                log.warning("analytics_boot_pass_failed", extra={"error": str(exc)})

        self._boot_task = asyncio.create_task(_boot_pass())
        try:
            from ats.services.market_data.calendar import IST
            tz = {"timezone": IST}
        except Exception:  # noqa: BLE001
            tz = {}
        ctx.scheduler.add_job(
            self.run_close_pass, "cron", hour=15, minute=50,
            id="analytics_close", max_instances=1, coalesce=True, **tz,
        )
        ctx.scheduler.add_job(
            self.run_poll_pass, "interval", minutes=1,
            id="analytics_poll", max_instances=1, coalesce=True,
        )
        log.info("analytics_started")

    # --- passes -----------------------------------------------------------------
    def run_close_pass(self) -> int:
        """Compute + persist a snapshot for every watchlist symbol."""
        n = 0
        for symbol in self._watchlist():
            if symbol.startswith("^"):
                continue
            df = self._history(symbol)
            if df is None or df.empty:
                continue
            payload = self.compute_snapshot(symbol, df)
            self._persist(symbol, payload)
            n += 1
        self.run_poll_pass()
        log.info("analytics_close_pass", extra={"symbols": n})
        return n

    def run_poll_pass(self) -> dict:
        """Recompute movers from the latest bars (in-memory)."""
        stats: dict[str, intraday.DayStat] = {}
        for symbol in self._watchlist():
            if symbol.startswith("^"):
                continue
            df = self._history(symbol)
            if df is None or len(df) < 2:
                continue
            close = df["close"]
            prev = float(close.iloc[-2])
            pct = (float(close.iloc[-1]) / prev - 1.0) * 100.0 if prev else 0.0
            vol = float(df["volume"].iloc[-1]) if "volume" in df else 0.0
            avg = float(df["volume"].iloc[-21:-1].mean()) if "volume" in df and len(df) >= 21 else vol
            stats[symbol] = intraday.DayStat(pct, vol, avg)
        self._movers = intraday.movers(stats)
        return self._movers

    def compute_snapshot(self, symbol: str, df: pd.DataFrame) -> dict:
        """Full analytics payload for one symbol (pure over the frame + DB fundamentals)."""
        price = float(df["close"].iloc[-1])
        ts = technical_summary(symbol, df)

        levels = {}
        if all(c in df.columns for c in ("high", "low", "close")):
            h, l, c = session_anchor(df, "D")
            levels["pivots"] = classic_pivots(h, l, c).as_dict()
            win = df.tail(252)
            levels["fib"] = fibonacci_retracements(
                float(win["high"].max()), float(win["low"].min()), "down"
            )

        pats = [p.as_dict() for p in patterns.detect(df)] if "open" in df.columns else []

        fv = self._fair_value(symbol, price)
        fund = self._fundamentals_row(symbol)

        near_high_pct = None
        win = df.tail(252)
        hi = float(win["high"].max()) if "high" in df else None
        if hi:
            near_high_pct = round((price / hi - 1.0) * 100.0, 2)  # 0 = at the high, negative = below

        metrics = {
            "price": round(price, 2),
            "tech_score": ts.score,
            "tech_label": ts.label,
            "mos_pct": None if not fv else fv.get("margin_of_safety_pct"),
            "verdict": None if not fv else fv.get("verdict"),
            "f_score": None if not fv else fv.get("quality", {}).get("f_score"),
            "pe": fund.get("pe"),
            "pb": fund.get("pb"),
            "roe": fund.get("roe"),
            "dividend_yield": fund.get("dividend_yield"),
            "near_high_pct": near_high_pct,
        }

        return {
            "symbol": symbol,
            "day": date.today().isoformat(),
            "price": round(price, 2),
            "summary": ts.as_dict(),
            "levels": levels,
            "patterns": pats,
            "fair_value": fv,
            "metrics": metrics,
        }

    # --- accessors --------------------------------------------------------------
    def get(self, symbol: str) -> dict | None:
        """Latest persisted snapshot payload for a symbol."""
        with session_scope() as s:
            row = s.execute(
                select(AnalyticsSnapshot).where(AnalyticsSnapshot.symbol == symbol)
                .order_by(AnalyticsSnapshot.day.desc()).limit(1)
            ).scalar_one_or_none()
            return dict(row.payload) if row else None

    def table(self) -> list[dict]:
        """One metrics row per symbol (latest snapshot) — the screener feed."""
        rows: list[dict] = []
        with session_scope() as s:
            snaps = s.execute(
                select(AnalyticsSnapshot).order_by(AnalyticsSnapshot.day.desc())
            ).scalars().all()
        seen: set[str] = set()
        for snap in snaps:
            if snap.symbol in seen:
                continue
            seen.add(snap.symbol)
            m = dict(snap.payload.get("metrics", {}))
            m["symbol"] = snap.symbol
            rows.append(m)
        return rows

    def movers(self) -> dict:
        return self._movers

    def screener(self, preset: str | None = None) -> list[dict]:
        """Filter the metrics table by a named preset (value/quality/dividend/
        momentum). Unknown/empty preset returns the full table."""
        rows = self.table()
        key = (preset or "").lower()
        pred = _PRESETS.get(key)
        if pred is None:
            return rows
        out = [r for r in rows if pred(r)]
        # Valuation screens rank by margin of safety (cheapest / dearest first).
        if key == "undervalued":
            out.sort(key=lambda r: (r.get("mos_pct") if r.get("mos_pct") is not None else -1e9), reverse=True)
        elif key == "overvalued":
            out.sort(key=lambda r: (r.get("mos_pct") if r.get("mos_pct") is not None else 1e9))
        return out

    def presets(self) -> list[str]:
        return list(_PRESETS.keys())

    # --- internals --------------------------------------------------------------
    def _persist(self, symbol: str, payload: dict) -> None:
        today = date.today()
        with session_scope() as s:
            row = s.execute(
                select(AnalyticsSnapshot).where(
                    AnalyticsSnapshot.symbol == symbol, AnalyticsSnapshot.day == today
                )
            ).scalar_one_or_none()
            if row is None:
                row = AnalyticsSnapshot(symbol=symbol, day=today)
                s.add(row)
            row.payload = payload

    def _fair_value(self, symbol: str, price: float) -> dict | None:
        try:
            from ats.services.fundamentals.fair_value import fair_value
            return fair_value(symbol, price=price)
        except Exception as exc:  # noqa: BLE001
            log.warning("analytics_fair_value_failed", extra={"symbol": symbol, "error": str(exc)})
            return None

    def _fundamentals_row(self, symbol: str) -> dict:
        f = self._orch.get("fundamentals") if self._orch else None
        if f is not None:
            try:
                row = f.get(symbol)
                if row:
                    return dict(row)
            except Exception:  # noqa: BLE001
                pass
        return {}

    def _watchlist(self) -> list[str]:
        if self._md is not None:
            try:
                return list(self._md.watchlist())
            except Exception:  # noqa: BLE001
                pass
        from ats.services.reference import UNIVERSE
        return [sym for sym, _n, _s, itype in UNIVERSE if itype in ("EQ", "ETF")]

    def _history(self, symbol: str) -> pd.DataFrame | None:
        if self._md is not None:
            try:
                return self._md.get_history(symbol, limit=400)
            except Exception:  # noqa: BLE001
                return None
        return None
