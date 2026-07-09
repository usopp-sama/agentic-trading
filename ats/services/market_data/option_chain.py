"""NSE option-chain sources (Indian market).

Two interchangeable sources behind ``fetch(symbol, spot=None)``:

- ``NseOptionChain``: the public nseindia.com option-chain API for index
  options (NIFTY/BANKNIFTY). NSE requires a browser-like session: a
  warm-up GET on the homepage collects cookies before the API call, and
  requests carry standard browser headers. Failures return ``None`` —
  callers must degrade gracefully (NSE throttles aggressively).
- ``SyntheticOptionChain``: deterministic offline chain whose ATM IV and
  put-call ratio derive from a (symbol, date) hash, so the IV monitor,
  dashboard, and the future vol-premium sleeve are developable and
  testable with zero network.

Only summary statistics are extracted (spot, nearest expiry, ATM IV,
PCR) — that is what the vol-premium logic needs; full per-strike chains
can be persisted later when strategies require them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from ats.core.logging import get_logger

log = get_logger("ats.option_chain")

# NSE moved index weekly expiries to Tuesday (SEBI's 2025 one-expiry-per-
# exchange rationalization). Update here if the exchange shifts again.
NSE_WEEKLY_EXPIRY_WEEKDAY = 1  # Tuesday


@dataclass(frozen=True)
class OptionChainSummary:
    symbol: str
    expiry: str          # ISO date of the nearest expiry
    spot: float
    atm_strike: float
    atm_iv: float        # decimal, 0.14 = 14%
    pcr: float           # put-call open-interest ratio
    ts: str              # ISO timestamp of the snapshot
    source: str

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "expiry": self.expiry,
            "spot": self.spot,
            "atm_strike": self.atm_strike,
            "atm_iv": self.atm_iv,
            "pcr": self.pcr,
            "ts": self.ts,
            "source": self.source,
        }


class OptionChainSource(Protocol):
    def fetch(
        self, symbol: str, spot: float | None = None
    ) -> OptionChainSummary | None: ...


def _next_expiry(today: date, weekday: int = NSE_WEEKLY_EXPIRY_WEEKDAY) -> date:
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # an expiry today rolls to next week after close
    return today + timedelta(days=days_ahead)


def _unit_hash(*parts: str) -> float:
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return int(digest[:12], 16) / float(16**12)


class SyntheticOptionChain:
    """Deterministic chain summary for offline development."""

    def fetch(
        self, symbol: str, spot: float | None = None
    ) -> OptionChainSummary | None:
        now = datetime.now(timezone.utc)
        day = now.date()
        spot = float(spot) if spot else 100.0
        # IV in [10%, 28%] and PCR in [0.7, 1.3], stable within a day.
        atm_iv = 0.10 + 0.18 * _unit_hash("iv", symbol, day.isoformat())
        pcr = 0.7 + 0.6 * _unit_hash("pcr", symbol, day.isoformat())
        step = max(1.0, round(spot * 0.01))
        return OptionChainSummary(
            symbol=symbol,
            expiry=_next_expiry(day).isoformat(),
            spot=round(spot, 2),
            atm_strike=round(round(spot / step) * step, 2),
            atm_iv=round(atm_iv, 4),
            pcr=round(pcr, 3),
            ts=now.isoformat(),
            source="synthetic",
        )


class NseOptionChain:  # pragma: no cover - live network source
    """Index option chain from the public nseindia.com API."""

    _BASE = "https://www.nseindia.com"
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/option-chain",
    }

    def fetch(
        self, symbol: str, spot: float | None = None
    ) -> OptionChainSummary | None:
        import httpx

        try:
            with httpx.Client(headers=self._HEADERS, timeout=15.0) as client:
                client.get(self._BASE)  # warm-up: collects session cookies
                resp = client.get(
                    f"{self._BASE}/api/option-chain-indices",
                    params={"symbol": symbol},
                )
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:  # noqa: BLE001 - NSE throttles; degrade, don't crash
            log.warning("nse_option_chain_failed", extra={"symbol": symbol, "error": str(exc)})
            return None

        try:
            records = payload["records"]
            underlying = float(records["underlyingValue"])
            expiry = records["expiryDates"][0]
            rows = [r for r in records["data"] if r.get("expiryDate") == expiry]
            atm_row = min(
                rows, key=lambda r: abs(float(r["strikePrice"]) - underlying)
            )
            ivs = [
                float(atm_row[leg]["impliedVolatility"])
                for leg in ("CE", "PE")
                if leg in atm_row and atm_row[leg].get("impliedVolatility")
            ]
            ce_oi = sum(float(r["CE"]["openInterest"]) for r in rows if "CE" in r)
            pe_oi = sum(float(r["PE"]["openInterest"]) for r in rows if "PE" in r)
            if not ivs or ce_oi <= 0:
                return None
            return OptionChainSummary(
                symbol=symbol,
                expiry=expiry,
                spot=round(underlying, 2),
                atm_strike=float(atm_row["strikePrice"]),
                atm_iv=round(sum(ivs) / len(ivs) / 100.0, 4),
                pcr=round(pe_oi / ce_oi, 3),
                ts=datetime.now(timezone.utc).isoformat(),
                source="nse",
            )
        except (KeyError, ValueError, IndexError) as exc:
            log.warning("nse_option_chain_parse_failed", extra={"symbol": symbol, "error": str(exc)})
            return None


def build_option_chain_source() -> OptionChainSource:
    """Honors ``ATS_OPTION_CHAIN_SOURCE``; ``auto`` follows the data source."""
    from ats.core.config import get_settings

    settings = get_settings()
    choice = settings.option_chain_source
    if choice == "auto":
        choice = "synthetic" if settings.data_source == "synthetic" else "nse"
    if choice == "nse":
        return NseOptionChain()
    return SyntheticOptionChain()
