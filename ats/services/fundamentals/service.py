"""Fundamentals Service.

Refreshes fundamental ratios for the active NSE universe on start and
then daily, persists each refresh (so ratio history accumulates), and
serves as the in-process oracle for the factor sleeve, screener, and
agents. Symbols without fundamentals (indices, ETFs) are simply absent
from the cache — consumers treat missing as missing.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Fundamental
from ats.services.fundamentals.providers import (
    FundamentalSnapshot,
    build_fundamentals_provider,
)
from sqlalchemy import select

log = get_logger("ats.fundamentals")


class FundamentalsService:
    name = "fundamentals"

    def __init__(self) -> None:
        self.provider = build_fundamentals_provider()
        self._md = None
        self._cache: dict[str, dict] = {}

    async def start(self, ctx) -> None:
        self._md = ctx.orchestrator.get("market_data")
        self.refresh_all()
        hours = get_settings().fundamentals_refresh_hours
        ctx.scheduler.add_job(
            self.refresh_all,
            "interval",
            hours=hours,
            id="fundamentals_refresh",
            max_instances=1,
            coalesce=True,
        )

    # --- refresh -------------------------------------------------------------
    def refresh_all(self) -> int:
        symbols = self._md.watchlist() if self._md is not None else []
        refreshed = 0
        for symbol in symbols:
            try:
                snap = self.provider.fetch(symbol)
            except Exception as exc:  # noqa: BLE001
                log.warning("fundamentals_error", extra={"symbol": symbol, "error": str(exc)})
                continue
            if snap is None:
                continue
            self._cache[symbol] = snap.as_dict()
            self._persist(snap)
            refreshed += 1
        log.info("fundamentals_refreshed", extra={"symbols": refreshed})
        return refreshed

    @staticmethod
    def _persist(snap: FundamentalSnapshot) -> None:
        with session_scope() as s:
            row = s.execute(
                select(Fundamental).where(
                    Fundamental.symbol == snap.symbol,
                    Fundamental.as_of == snap.as_of,
                )
            ).scalar_one_or_none()
            if row is None:
                row = Fundamental(symbol=snap.symbol, as_of=snap.as_of)
                s.add(row)
            row.pe = snap.pe
            row.pb = snap.pb
            row.roe = snap.roe
            row.debt_to_equity = snap.debt_to_equity
            row.profit_margin = snap.profit_margin
            row.dividend_yield = snap.dividend_yield
            row.market_cap = snap.market_cap
            row.source = snap.source

    # --- accessors -------------------------------------------------------------
    def get(self, symbol: str) -> dict | None:
        return self._cache.get(symbol)

    def all_latest(self) -> dict[str, dict]:
        return dict(self._cache)
