"""Pluggable fundamentals providers (Indian market).

All providers expose ``fetch(symbol) -> FundamentalSnapshot | None``.

- ``SyntheticFundamentals``: deterministic ratios derived from the
  symbol hash, so the whole system (factor sleeve, screener, agents)
  runs offline with stable, realistic-looking values.
- ``YFinanceFundamentals``: live ratios via yfinance, which covers NSE
  symbols through the ``.NS`` suffix. Best-effort field mapping with
  normalization of yfinance quirks (``debtToEquity`` arrives as a
  percentage, e.g. 41.5 for 0.415).

A screener.in / NSE-filings provider can slot in later behind the same
interface — that is the reason the interface exists.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ats.core.logging import get_logger

log = get_logger("ats.fundamentals")


@dataclass(frozen=True)
class FundamentalSnapshot:
    symbol: str
    as_of: date
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None              # decimal, 0.18 = 18%
    debt_to_equity: float | None = None   # ratio, 0.4 = 40% of equity
    profit_margin: float | None = None    # decimal
    dividend_yield: float | None = None   # decimal
    market_cap: float | None = None       # in INR for .NS symbols
    source: str = "synthetic"

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "as_of": self.as_of.isoformat(),
            "pe": self.pe,
            "pb": self.pb,
            "roe": self.roe,
            "debt_to_equity": self.debt_to_equity,
            "profit_margin": self.profit_margin,
            "dividend_yield": self.dividend_yield,
            "market_cap": self.market_cap,
            "source": self.source,
        }


class FundamentalsProvider(Protocol):
    def fetch(self, symbol: str) -> FundamentalSnapshot | None: ...


def _unit_hash(symbol: str, salt: str) -> float:
    """Deterministic uniform [0, 1) from (symbol, salt)."""
    digest = hashlib.sha256(f"{salt}:{symbol}".encode()).hexdigest()
    return int(digest[:12], 16) / float(16**12)


class SyntheticFundamentals:
    """Deterministic, plausible ratios for offline development.

    Indices and ETFs (``^`` prefix, BEES funds) have no company
    fundamentals and return ``None`` — same shape as a real provider.
    """

    _NON_EQUITY_MARKERS = ("^", "BEES")

    def fetch(self, symbol: str) -> FundamentalSnapshot | None:
        if any(m in symbol for m in self._NON_EQUITY_MARKERS):
            return None
        return FundamentalSnapshot(
            symbol=symbol,
            as_of=date.today(),
            pe=round(8.0 + 52.0 * _unit_hash(symbol, "pe"), 2),
            pb=round(0.8 + 11.0 * _unit_hash(symbol, "pb"), 2),
            roe=round(0.05 + 0.30 * _unit_hash(symbol, "roe"), 4),
            debt_to_equity=round(2.5 * _unit_hash(symbol, "de"), 4),
            profit_margin=round(0.03 + 0.27 * _unit_hash(symbol, "pm"), 4),
            dividend_yield=round(0.03 * _unit_hash(symbol, "dy"), 4),
            market_cap=round(5e10 + 2.5e12 * _unit_hash(symbol, "mc"), 0),
            source="synthetic",
        )


class YFinanceFundamentals:
    """Live fundamentals from yfinance (NSE symbols use the .NS suffix)."""

    def fetch(self, symbol: str) -> FundamentalSnapshot | None:  # pragma: no cover - network
        try:
            import yfinance as yf

            info = yf.Ticker(symbol).info or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("fundamentals_fetch_failed", extra={"symbol": symbol, "error": str(exc)})
            return None
        if not info or info.get("quoteType") not in (None, "EQUITY"):
            return None
        de = info.get("debtToEquity")
        if de is not None and de > 10.0:
            de = de / 100.0  # yfinance reports a percentage
        return FundamentalSnapshot(
            symbol=symbol,
            as_of=date.today(),
            pe=info.get("trailingPE"),
            pb=info.get("priceToBook"),
            roe=info.get("returnOnEquity"),
            debt_to_equity=de,
            profit_margin=info.get("profitMargins"),
            dividend_yield=info.get("dividendYield"),
            market_cap=info.get("marketCap"),
            source="yfinance",
        )


def build_fundamentals_provider() -> FundamentalsProvider:
    """Honors ``ATS_FUNDAMENTALS_SOURCE``; ``auto`` follows the data source."""
    from ats.core.config import get_settings

    settings = get_settings()
    choice = settings.fundamentals_source
    if choice == "auto":
        choice = "synthetic" if settings.data_source == "synthetic" else "yfinance"
    if choice == "yfinance":
        return YFinanceFundamentals()
    return SyntheticFundamentals()
