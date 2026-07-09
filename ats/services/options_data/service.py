"""Options Data Service.

Polls the NIFTY option chain on a schedule and turns it into the one
number the volatility-risk-premium logic cares about: **how rich is
implied volatility versus recent realized volatility** (roadmap Part
7.7). Publishes an OPTION_CHAIN event per snapshot and serves the
latest reading to the dashboard and agents.

This is intelligence, not execution: the system has no tradeable
options instruments yet, so no sleeve trades on this — it monitors the
premium so the defined-risk vol sleeve can be built on evidence when
options execution lands.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.services.market_data.calendar import is_polling_window
from ats.services.market_data.option_chain import build_option_chain_source
from quant.analysis.indicators import annualized_volatility

log = get_logger("ats.options_data")

_REALIZED_WINDOW = 21  # ~one trading month of daily closes


class OptionsDataService:
    name = "options_data"

    def __init__(self) -> None:
        self.source = build_option_chain_source()
        self._bus: EventBus | None = None
        self._md = None
        self._latest: dict | None = None

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._md = ctx.orchestrator.get("market_data")
        await self.poll()
        ctx.scheduler.add_job(
            self.poll,
            "interval",
            seconds=get_settings().option_chain_interval_s,
            id="option_chain_poll",
            max_instances=1,
            coalesce=True,
        )

    async def poll(self) -> None:
        settings = get_settings()
        # The option-chain IV/PCR snapshot is only meaningful during the NSE
        # session. Outside the polling window (and on a real chain source) skip
        # the poll instead of churning the live endpoint 24/7. Synthetic chains
        # keep flowing so dev/offline runs still exercise the sleeve.
        if (
            settings.respect_market_hours
            and settings.option_chain_source != "synthetic"
            and not is_polling_window()
        ):
            return
        ref = settings.regime_reference_symbol
        spot = self._md.latest_price(ref) if self._md is not None else None
        summary = self.source.fetch(settings.option_chain_symbol, spot=spot)
        if summary is None:
            return

        realized = self._realized_vol(ref)
        snapshot = summary.as_dict()
        snapshot["realized_vol_20d"] = realized
        snapshot["iv_premium"] = (
            round(summary.atm_iv - realized, 4) if realized is not None else None
        )
        self._latest = snapshot
        log.info(
            "option_chain_snapshot",
            extra={
                "symbol": summary.symbol,
                "atm_iv": summary.atm_iv,
                "pcr": summary.pcr,
                "iv_premium": snapshot["iv_premium"],
            },
        )
        if self._bus is not None:
            await self._bus.publish(Topic.OPTION_CHAIN, snapshot)

    def _realized_vol(self, ref: str) -> float | None:
        if self._md is None:
            return None
        df = self._md.get_history(ref, limit=_REALIZED_WINDOW + 1)
        if df.empty or len(df) < _REALIZED_WINDOW:
            return None
        vol = annualized_volatility(df["close"].tail(_REALIZED_WINDOW + 1))
        return round(float(vol), 4) if vol == vol else None  # NaN-safe

    # --- accessors -------------------------------------------------------------
    def latest(self) -> dict | None:
        return self._latest
