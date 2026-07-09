"""FlowsService: nightly flow collection + the pump-signature veto.

The legitimate version of "detect unusual flow and position around it"
(plan §4), built defensive-first:

- **Collect** (nightly, off-hours): delivery % and bulk deals from free NSE
  archives into ``flows_daily``. Failures degrade silently — no network,
  no problem, the signature just runs unconfirmed.
- **Score** every watchlist symbol's pump signature (price surge + volume
  z-spike + falling delivery) after each collection.
- **Publish** triggered names to the ``veto:flow`` kv key.

Modes (``ATS_FLOWS_VETO_MODE``): ``shadow`` (default) records and audits
what *would* have been vetoed — the evaluation the hypothesis registry
needs — without blocking anything; ``active`` makes EventRiskService
enforce it on new entries (exits always pass); ``off`` disables scoring.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy import select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import FlowDaily
from ats.services.flows import collectors
from ats.services.flows.signature import pump_signature

log = get_logger("ats.flows")

FLOW_VETO_KEY = "veto:flow"


class FlowsService:
    name = "flows"

    def __init__(self) -> None:
        self._md = None

    async def start(self, ctx) -> None:
        settings = get_settings()
        self._md = ctx.orchestrator.get("market_data")
        if not settings.flows_enabled:
            log.info("flows_disabled")
            return

        from ats.services.market_data.calendar import IST

        # Collect after the close, before the 20:00 research nightly, so the
        # slow loop reads fresh flow data and the veto is set for tomorrow.
        ctx.scheduler.add_job(
            self.collect_and_score, "cron", hour=19, minute=0, timezone=IST,
            id="flows_nightly", max_instances=1, coalesce=True,
        )
        # Re-score from stored data on boot (no network) so a restart does
        # not lose the current veto set.
        try:
            self.recompute_vetoes()
        except Exception as exc:  # noqa: BLE001 — boot must not fail on scoring
            log.warning("flows_boot_score_failed", extra={"error": str(exc)})
        log.info("flows_started", extra={"mode": settings.flows_veto_mode})

    # --- collection -------------------------------------------------------------
    def collect_and_score(self) -> dict:
        out = self.collect()
        out.update(self.recompute_vetoes())
        return out

    def collect(self, day: date | None = None) -> dict:
        """Pull delivery % + bulk deals into ``flows_daily`` (watchlist only)."""
        settings = get_settings()
        if settings.flows_source != "nse":
            return {"collected": 0, "source": settings.flows_source}
        day = day or date.today()
        watch = set(self._watchlist())

        delivery = [r for r in collectors.fetch_delivery(day) if r["symbol"] in watch]
        for row in delivery:
            self._upsert(row["symbol"], day, delivery_pct=row["delivery_pct"])

        deals = [r for r in collectors.fetch_bulk_deals() if r["symbol"] in watch]
        for row in deals:
            buy = row["qty"] if row["side"] == "BUY" else 0.0
            sell = row["qty"] if row["side"] == "SELL" else 0.0
            self._upsert(row["symbol"], row["day"], bulk_buy=buy, bulk_sell=sell)

        log.info("flows_collected",
                 extra={"day": day.isoformat(), "delivery_rows": len(delivery),
                        "deal_rows": len(deals)})
        return {"collected": len(delivery), "deals": len(deals)}

    # --- scoring ------------------------------------------------------------------
    def recompute_vetoes(self) -> dict:
        """Score every watchlist symbol; publish triggered names to kv."""
        settings = get_settings()
        if settings.flows_veto_mode == "off":
            state.set_kv(FLOW_VETO_KEY, {})
            return {"vetoed": 0, "mode": "off"}

        today = date.today()
        vetoes: dict[str, dict] = {}
        for symbol in self._watchlist():
            if symbol.startswith("^"):
                continue
            df = self._history(symbol)
            if df is None or df.empty:
                continue
            sig = pump_signature(
                symbol, df, self._delivery_series(symbol),
                px_chg_5d=settings.flows_px_chg_5d,
                vol_z=settings.flows_vol_z,
                delivery_drop=settings.flows_delivery_drop,
            )
            if sig.triggered:
                vetoes[symbol] = {
                    "day": today.isoformat(), "score": sig.score,
                    "reasons": sig.reasons,
                    "shadow": settings.flows_veto_mode != "active",
                }
                state.audit(
                    "flows",
                    "veto.flow" if settings.flows_veto_mode == "active"
                    else "veto.flow.shadow",
                    {"symbol": symbol, **vetoes[symbol]},
                )
                log.warning("flow_anomaly", extra={"symbol": symbol,
                                                   "score": sig.score,
                                                   "reasons": sig.reasons,
                                                   "mode": settings.flows_veto_mode})
        state.set_kv(FLOW_VETO_KEY, vetoes)
        return {"vetoed": len(vetoes), "mode": settings.flows_veto_mode}

    # --- introspection ---------------------------------------------------------------
    def status(self) -> dict:
        settings = get_settings()
        return {
            "enabled": settings.flows_enabled,
            "mode": settings.flows_veto_mode,
            "vetoes": state.get_kv(FLOW_VETO_KEY),
        }

    # --- internals ----------------------------------------------------------------------
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
                return self._md.get_history(symbol, limit=60)
            except Exception:  # noqa: BLE001
                return None
        from ats.services.market_data.store import load_history

        try:
            return load_history(symbol, limit=60)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _delivery_series(symbol: str, days: int = 40) -> pd.Series | None:
        cutoff = date.today() - timedelta(days=days * 2)
        with session_scope() as s:
            rows = s.execute(
                select(FlowDaily).where(
                    FlowDaily.symbol == symbol, FlowDaily.day >= cutoff,
                    FlowDaily.delivery_pct.isnot(None),
                ).order_by(FlowDaily.day)
            ).scalars().all()
        if not rows:
            return None
        return pd.Series([r.delivery_pct for r in rows],
                         index=[r.day for r in rows], dtype=float)

    @staticmethod
    def _upsert(symbol: str, day: date, delivery_pct: float | None = None,
                bulk_buy: float = 0.0, bulk_sell: float = 0.0) -> None:
        with session_scope() as s:
            row = s.execute(
                select(FlowDaily).where(FlowDaily.symbol == symbol,
                                        FlowDaily.day == day)
            ).scalar_one_or_none()
            if row is None:
                row = FlowDaily(symbol=symbol, day=day)
                s.add(row)
            if delivery_pct is not None:
                row.delivery_pct = float(delivery_pct)
            if bulk_buy or bulk_sell:
                row.bulk_buy_qty += float(bulk_buy)
                row.bulk_sell_qty += float(bulk_sell)
                row.deals += 1
