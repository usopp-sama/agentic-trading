"""Metrics Service — research instrumentation for the month-long paper run.

Once a day (shortly after the NSE close, after sleeves and the learning loop
have marked the day) this exports two snapshots to ``var/metrics/`` and appends
to a reproducible research log:

- ``strategies_YYYY-MM-DD.parquet`` — per-strategy sleeve performance (equity,
  rolling Sharpe, max drawdown, holdings) joined with the live registry row
  (status, capital weight, allocation %). This is the per-strategy track record
  used for month-end A/B comparisons and the shadow->paper promotion gate.
- ``smes_YYYY-MM-DD.parquet`` — per-SME track record (n, hit rate, Brier,
  vote/promoted weight, pnl contribution, status) from the learning loop.
- ``research_log.jsonl`` — append-only: the active strategy params in force plus
  a one-line performance summary, so a given day's numbers can always be tied
  back to the exact configuration that produced them.

Parquet keeps the columnar history cheap to load into pandas for offline
analysis. The service degrades gracefully: if a dependency or sibling service
is missing it logs and skips rather than crashing the run.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import SmeTrackRecord, Strategy as StrategyRow

log = get_logger("ats.metrics")

# The tunable params that define each shadow strategy's configuration, recorded
# in the research log so performance is always reproducible from config.
_PARAM_KEYS = (
    "xs_mom_formation", "xs_mom_skip", "xs_mom_decile", "xs_mom_rebalance_days",
    "dual_mom_lookback", "dual_mom_top_n", "high52_buy_near", "high52_sell_near",
    "macd_adx_min", "st_reversal_lookback", "st_reversal_decile",
    "ou_keltner_ema", "ou_keltner_atr", "ou_keltner_z_entry", "ou_keltner_z_exit",
    "factor_sleeve_top_n", "factor_sleeve_rebalance_days",
    "coint_formation", "coint_z_window", "coint_entry_z", "coint_exit_z",
    "coint_reselect_days", "pead_gap_z", "pead_drift_days",
    "news_sent_buy", "news_sent_sell", "news_sent_min_count",
    "tom_days_before", "tom_days_after", "vol_target_annual", "vol_target_max",
    "sleeve_allocation_method", "learning_horizon_days",
)


class MetricsService:
    name = "metrics"

    def __init__(self) -> None:
        self._strategies = None
        self._learning = None
        self._dir = Path(get_settings().metrics_dir)

    async def start(self, ctx) -> None:
        settings = get_settings()
        if not settings.metrics_export_enabled:
            log.info("metrics_export_disabled")
            return
        self._strategies = ctx.orchestrator.get("strategies")
        self._learning = ctx.orchestrator.get("learning")
        self._dir.mkdir(parents=True, exist_ok=True)
        from ats.services.market_data.calendar import IST

        ctx.scheduler.add_job(
            self.export_daily, "cron",
            hour=settings.metrics_export_hour, minute=settings.metrics_export_minute,
            timezone=IST, id="metrics_export", max_instances=1, coalesce=True,
        )
        # One snapshot on boot so there is always a baseline to inspect.
        try:
            self.export_daily()
        except Exception as exc:  # noqa: BLE001
            log.warning("metrics_initial_export_failed", extra={"error": str(exc)})

    # --- export -------------------------------------------------------------
    def export_daily(self) -> dict:
        day = date.today()
        strat_rows = self._strategy_metrics()
        sme_rows = self._sme_metrics()
        written: list[str] = []
        if strat_rows:
            path = self._dir / f"strategies_{day.isoformat()}.parquet"
            pd.DataFrame(strat_rows).to_parquet(path, index=False)
            written.append(path.name)
        if sme_rows:
            path = self._dir / f"smes_{day.isoformat()}.parquet"
            pd.DataFrame(sme_rows).to_parquet(path, index=False)
            written.append(path.name)
        self._append_research_log(day, strat_rows, sme_rows)
        log.info("metrics_exported", extra={"day": day.isoformat(), "files": written,
                                            "strategies": len(strat_rows), "smes": len(sme_rows)})
        return {"day": day.isoformat(), "files": written}

    def _strategy_metrics(self) -> list[dict]:
        # Live registry rows (status / capital weight / allocation %).
        with session_scope() as s:
            registry = {
                r.id: {"name": r.name, "type": r.type, "status": r.status,
                       "weight": r.weight, "allocation_pct": r.allocation_pct}
                for r in s.execute(select(StrategyRow)).scalars().all()
            }
        # Sleeve track record from the in-memory tracker, if available.
        sleeve_stats = {}
        if self._strategies is not None:
            try:
                sleeve_stats = {row["strategy"]: row for row in self._strategies.sleeve_stats()}
            except Exception as exc:  # noqa: BLE001
                log.warning("sleeve_stats_failed", extra={"error": str(exc)})
        today = date.today().isoformat()
        rows: list[dict] = []
        for sid in sorted(set(registry) | set(sleeve_stats)):
            reg = registry.get(sid, {})
            st = sleeve_stats.get(sid, {})
            rows.append({
                "day": today,
                "strategy": sid,
                "name": reg.get("name"),
                "type": reg.get("type"),
                "status": reg.get("status"),
                "weight": reg.get("weight"),
                "allocation_pct": reg.get("allocation_pct"),
                "sleeve_equity": st.get("equity"),
                "sleeve_days": st.get("days"),
                "sleeve_sharpe": st.get("sharpe"),
                "sleeve_max_drawdown": st.get("max_drawdown"),
                "holdings": len(st.get("holdings", [])) if st else None,
                "alloc_weight": st.get("alloc_weight"),
            })
        return rows

    def _sme_metrics(self) -> list[dict]:
        today = date.today().isoformat()
        with session_scope() as s:
            rows = s.execute(select(SmeTrackRecord)).scalars().all()
            return [{
                "day": today,
                "sme": r.sme,
                "n": r.n,
                "wins": r.wins,
                "hit_rate": r.hit_rate,
                "brier": r.brier,
                "pnl_contrib": r.pnl_contrib,
                "vote_weight": r.vote_weight,
                "promoted_weight": r.promoted_weight,
                "status": r.status,
            } for r in rows]

    def _append_research_log(self, day: date, strat_rows: list[dict], sme_rows: list[dict]) -> None:
        settings = get_settings()
        params = {k: getattr(settings, k, None) for k in _PARAM_KEYS}
        # Compact rolling-performance summary for quick scanning.
        ranked = sorted(
            (r for r in strat_rows if r.get("sleeve_sharpe") is not None),
            key=lambda r: r["sleeve_sharpe"], reverse=True,
        )
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "day": day.isoformat(),
            "params": params,
            "n_strategies": len(strat_rows),
            "n_smes": len(sme_rows),
            "top_sleeves": [
                {"strategy": r["strategy"], "sharpe": r["sleeve_sharpe"],
                 "equity": r["sleeve_equity"], "status": r["status"]}
                for r in ranked[:5]
            ],
            "best_sme": max(
                ((r["sme"], r["hit_rate"], r["n"]) for r in sme_rows),
                default=None, key=lambda t: (t[1], t[2]),
            ),
        }
        path = self._dir / "research_log.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
