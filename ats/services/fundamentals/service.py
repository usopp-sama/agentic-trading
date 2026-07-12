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
        self._itypes: dict[str, str] = {}
        self._consecutive_failures = 0

    def _load_instrument_types(self) -> None:
        """Cache instrument types so we never ask a data vendor for company
        fundamentals on an index or a commodity future (they have none, and
        the live vendor answers such lookups with a 401 + noisy stack)."""
        from ats.core.models import Instrument

        try:
            with session_scope() as s:
                self._itypes = {
                    r.symbol: r.instrument_type
                    for r in s.execute(select(Instrument)).scalars().all()
                }
        except Exception as exc:  # noqa: BLE001 - fall back to fetching all
            log.warning("fundamentals_itypes_load_failed", extra={"error": str(exc)})

    async def start(self, ctx) -> None:
        self._md = ctx.orchestrator.get("market_data")
        self._load_instrument_types()
        self.refresh_all()
        s = get_settings()
        ctx.scheduler.add_job(
            self.refresh_all,
            "interval",
            hours=s.fundamentals_refresh_hours,
            id="fundamentals_refresh",
            max_instances=1,
            coalesce=True,
        )
        # Statement lines refresh weekly, off-hours (Sun 18:00 IST) — never on
        # start and never in the poll path (QA-10: keep network work off-session).
        if s.statements_enabled and s.statements_source != "none":
            ctx.scheduler.add_job(
                self.refresh_statements,
                "cron",
                day_of_week="sun",
                hour=18,
                minute=0,
                id="statements_refresh",
                max_instances=1,
                coalesce=True,
            )

    # --- refresh -------------------------------------------------------------
    def refresh_all(self) -> int:
        symbols = self._md.watchlist() if self._md is not None else []
        refreshed = 0
        skipped = 0
        self._consecutive_failures = 0   # fresh pass, fresh breaker
        for symbol in symbols:
            # Only equities have company fundamentals. Skip indices/ETFs/
            # commodities up front (known type, non-EQ) so we never make a
            # doomed vendor call. Unknown symbols fall through to the provider.
            itype = self._itypes.get(symbol)
            if itype is not None and itype != "EQ":
                skipped += 1
                continue
            try:
                snap = self.provider.fetch(symbol)
            except Exception as exc:  # noqa: BLE001
                log.warning("fundamentals_error", extra={"symbol": symbol, "error": str(exc)})
                snap = None
            if snap is None:
                self._consecutive_failures += 1
                # Circuit-break: a blocked/rate-limited vendor used to grind
                # through the whole watchlist with ~10s of 401 retries each.
                if self._consecutive_failures >= 3:
                    log.warning("fundamentals_circuit_break",
                                extra={"refreshed": refreshed})
                    break
                continue
            self._consecutive_failures = 0
            self._cache[symbol] = snap.as_dict()
            self._persist(snap)
            refreshed += 1
        log.info("fundamentals_refreshed", extra={"symbols": refreshed, "skipped": skipped})
        return refreshed

    def refresh_statements(self) -> int:
        """Fetch + persist financial-statement lines for the EQ watchlist.

        Weekly, off-hours. Best-effort per symbol; a failed fetch simply
        contributes no rows (the fair-value surface then refuses that name
        rather than guessing). Not called on start — no boot-time network."""
        from ats.services.fundamentals.statements import (
            fetch_statements,
            persist_statements,
        )

        s = get_settings()
        symbols = self._md.watchlist() if self._md is not None else []
        written = 0
        for symbol in symbols:
            itype = self._itypes.get(symbol)
            if itype is not None and itype != "EQ":
                continue
            try:
                snaps = fetch_statements(symbol, source=s.statements_source)
            except Exception as exc:  # noqa: BLE001
                log.warning("statements_error", extra={"symbol": symbol, "error": str(exc)})
                continue
            if snaps:
                written += persist_statements(snaps)
        log.info("statements_refreshed", extra={"rows": written})
        return written

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
