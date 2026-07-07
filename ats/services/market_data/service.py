"""Market Data Service.

On start it backfills history for the active universe, then polls on a
schedule, persisting new bars, publishing BAR events, and emitting
VOLUME_SPIKE events when unusual activity is detected. It also serves as the
in-process price oracle other services query (paper broker, strategies,
agents).
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Instrument
from ats.services.market_data.calendar import is_polling_window, is_provisional_year
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
        self._quote_ts: dict[str, float] = {}  # symbol -> monotonic-ish epoch of last refresh
        self._symbols: list[str] = []
        self._closed_logged = False
        self._was_degraded = False

    # --- lifecycle ---------------------------------------------------------
    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._symbols = self._load_watchlist()
        # One batched download warms the cache for all symbols at once.
        prefetch = getattr(self.source, "prefetch", None)
        if prefetch is not None:
            prefetch(self._symbols)
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
        if self._market_closed():
            return
        for symbol in self._symbols:
            try:
                await self._poll_symbol(symbol)
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_failed", extra={"symbol": symbol, "error": str(exc)})
        await self._check_feed_degradation()

    async def _check_feed_degradation(self) -> None:
        """Alert once when the live feed degrades to mostly-synthetic, and once
        when it recovers. New entries are halted while degraded (enforced in the
        execution service via ``feed_healthy``)."""
        status = self.data_status()
        degraded = bool(status.get("degraded"))
        if degraded and not self._was_degraded:
            log.warning("feed_degraded", extra=status)
            if self._bus is not None:
                await self._bus.publish(
                    Topic.ALERT,
                    {"kind": "feed", "reason": "live feed degraded to synthetic fallback",
                     "live": status["live"], "total": status["total"], "ratio": status["ratio"]},
                )
        elif not degraded and self._was_degraded:
            log.info("feed_recovered", extra=status)
            if self._bus is not None:
                await self._bus.publish(
                    Topic.ALERT, {"kind": "feed", "reason": "live feed recovered",
                                  "ratio": status["ratio"]},
                )
        self._was_degraded = degraded

    def _market_closed(self) -> bool:
        """Gate LIVE sources to NSE hours; synthetic keeps flowing for dev."""
        from ats.core.config import get_settings

        settings = get_settings()
        if settings.data_source == "synthetic" or not settings.respect_market_hours:
            return False
        if is_polling_window():
            return False
        if not self._closed_logged:
            log.info("market_closed_polling_paused", extra={"source": settings.data_source})
            self._closed_logged = True
        return True

    async def _poll_symbol(self, symbol: str) -> None:
        self._closed_logged = False
        df = self.source.poll(symbol)
        added = upsert_bars(symbol, df)
        self._history[symbol] = df
        last_close = float(df["close"].iloc[-1])
        self._last_price[symbol] = last_close
        import time as _time

        self._quote_ts[symbol] = _time.time()
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

    def quote_age_s(self, symbol: str) -> float | None:
        """Seconds since this symbol's quote was last refreshed by a poll;
        None if it has not been polled this session (startup backfill does
        not count — a fill must never price off a stale cache)."""
        import time as _time

        ts = self._quote_ts.get(symbol)
        if ts is None:
            return None
        return max(0.0, _time.time() - ts)

    def intraday(self, symbol: str, interval: str = "5m", limit: int = 300) -> list[dict]:
        """Intraday candles from the source when it supports them (nse_live);
        empty otherwise so callers fall back to the persisted daily store."""
        fn = getattr(self.source, "intraday", None)
        if fn is None:
            return []
        try:
            return fn(symbol, interval=interval, limit=limit)
        except Exception as exc:  # noqa: BLE001
            log.warning("intraday_failed", extra={"symbol": symbol, "error": str(exc)})
            return []

    def watchlist(self) -> list[str]:
        return list(self._symbols)

    def reload_watchlist(self) -> list[str]:
        """Re-read the active universe (after an edit) and backfill new names."""
        from ats.services.market_data.store import upsert_bars

        self._symbols = self._load_watchlist()
        for sym in self._symbols:
            if sym in self._history:
                continue
            try:
                df = self.source.poll(sym)
                upsert_bars(sym, df)
                self._history[sym] = df
                self._last_price[sym] = float(df["close"].iloc[-1])
            except Exception as exc:  # noqa: BLE001
                log.warning("watchlist_backfill_failed", extra={"symbol": sym, "error": str(exc)})
        return self._symbols

    def data_status(self) -> dict:
        """Report how many symbols are on the live feed vs synthetic fallback,
        plus a ``degraded`` flag (live source expected this session, but most
        symbols fell back to synthetic)."""
        from ats.core.config import get_settings

        settings = get_settings()
        total = len(self._symbols)
        in_session = is_polling_window()
        is_live = getattr(self.source, "is_live", None)
        if is_live is None:
            # Pure synthetic source: intentional, never "degraded".
            return {"mode": "synthetic", "live": 0, "total": total, "ratio": 0.0,
                    "degraded": False, "in_session": in_session,
                    "provisional_calendar": is_provisional_year(date.today().year)}
        live = sum(1 for s in self._symbols if is_live(s))
        ratio = (live / total) if total else 0.0
        degraded = bool(
            settings.data_source != "synthetic"
            and in_session
            and total > 0
            and ratio < settings.feed_min_live_ratio
        )
        return {
            "mode": "live" if live else "synthetic",
            "live": live,
            "total": total,
            "ratio": round(ratio, 3),
            "degraded": degraded,
            "in_session": in_session,
            "provisional_calendar": is_provisional_year(date.today().year),
        }

    def feed_healthy(self) -> bool:
        """False when the live feed has degraded to mostly-synthetic in-session.
        Used by execution to halt NEW entries on bad data."""
        return not self.data_status().get("degraded", False)

    @staticmethod
    def _load_watchlist() -> list[str]:
        with session_scope() as s:
            return list(
                s.execute(
                    select(Instrument.symbol).where(Instrument.active.is_(True))
                ).scalars().all()
            )
