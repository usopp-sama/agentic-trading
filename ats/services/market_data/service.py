"""Market Data Service.

On start it backfills history for the active universe, then polls on a
schedule, persisting new bars, publishing BAR events, and emitting
VOLUME_SPIKE events when unusual activity is detected. It also serves as the
in-process price oracle other services query (paper broker, strategies,
agents).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Instrument
from ats.services.market_data.sources import build_data_source
from ats.services.market_data.store import load_history, upsert_bars

log = get_logger("ats.market_data")

_SPIKE_LOOKBACK = 30
_SPIKE_Z = 3.0
_SPIKE_MULT = 2.0


class MarketDataService:
    name = "market_data"

    def __init__(self) -> None:
        self.source = build_data_source()
        self._bus: EventBus | None = None
        self._history: dict[str, pd.DataFrame] = {}
        self._last_price: dict[str, float] = {}
        self._symbols: list[str] = []

    # --- lifecycle ---------------------------------------------------------
    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._symbols = self._load_watchlist()
        backfilled = 0
        for symbol in self._symbols:
            try:
                df = self.source.poll(symbol)
                upsert_bars(symbol, df)
                self._history[symbol] = df
                self._last_price[symbol] = float(df["close"].iloc[-1])
                backfilled += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("backfill_failed", extra={"symbol": symbol, "error": str(exc)})
        log.info("market_data_backfilled", extra={"symbols": backfilled})

        from ats.core.config import get_settings

        interval = get_settings().market_scan_interval_s
        ctx.scheduler.add_job(
            self.poll_all,
            "interval",
            seconds=interval,
            id="market_data_poll",
            max_instances=1,
            coalesce=True,
        )

    # --- polling -----------------------------------------------------------
    async def poll_all(self) -> None:
        for symbol in self._symbols:
            try:
                await self._poll_symbol(symbol)
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_failed", extra={"symbol": symbol, "error": str(exc)})

    async def _poll_symbol(self, symbol: str) -> None:
        df = self.source.poll(symbol)
        added = upsert_bars(symbol, df)
        self._history[symbol] = df
        last_close = float(df["close"].iloc[-1])
        self._last_price[symbol] = last_close
        if self._bus is not None:
            await self._bus.publish(
                Topic.BAR,
                {"symbol": symbol, "close": last_close, "new_bars": added},
            )
            spike = self._detect_volume_spike(df)
            if spike is not None:
                spike["symbol"] = symbol
                await self._bus.publish(Topic.VOLUME_SPIKE, spike)
                log.info("volume_spike", extra=spike)

    @staticmethod
    def _detect_volume_spike(df: pd.DataFrame) -> dict | None:
        vols = df["volume"].tail(_SPIKE_LOOKBACK + 1).to_numpy()
        if len(vols) < _SPIKE_LOOKBACK + 1:
            return None
        hist, last = vols[:-1], float(vols[-1])
        mean = float(np.mean(hist))
        std = float(np.std(hist))
        if std <= 0 or mean <= 0:
            return None
        z = (last - mean) / std
        if z >= _SPIKE_Z and last >= _SPIKE_MULT * mean:
            return {"volume": last, "mean_volume": mean, "zscore": round(z, 2)}
        return None

    # --- accessors used by other services ---------------------------------
    def get_history(self, symbol: str, limit: int = 250) -> pd.DataFrame:
        if symbol in self._history:
            return self._history[symbol].tail(limit)
        return load_history(symbol, limit=limit)

    def latest_price(self, symbol: str) -> float | None:
        return self._last_price.get(symbol)

    def watchlist(self) -> list[str]:
        return list(self._symbols)

    @staticmethod
    def _load_watchlist() -> list[str]:
        with session_scope() as s:
            return list(
                s.execute(
                    select(Instrument.symbol).where(Instrument.active.is_(True))
                ).scalars().all()
            )
