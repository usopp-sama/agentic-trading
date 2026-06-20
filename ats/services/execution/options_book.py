"""Paper execution for defined-risk index option structures.

The equity paper broker trades shares; options need different mechanics:
lots not shares, premium received up front, margin reserved against the
worst case, and settlement at expiry. This book implements exactly the
subset the vol-premium sleeve needs — **credit spreads** (and iron
condors as two of them) — and nothing more, because defined-risk-only
is a roadmap rule (7.7), not a simplification.

Every position's loss is bounded by construction:

    max loss per unit = (width between strikes) - (credit received)

and that amount × lot size × lots is reserved as margin at open. The
book can therefore never lose more than it reserved — the property the
tests assert by slamming the spot price far through the strikes.

Marking uses Black-Scholes with the chain's ATM IV (a flat-vol
approximation — honest enough for paper, noted in features).
Pure Python state machine; the VolPremiumService owns scheduling.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date

from quant.options import bs_price

_KINDS = ("CE", "PE")


@dataclass
class CreditSpread:
    """Short one strike, long a further-out wing; same kind and expiry."""

    spread_id: int
    symbol: str
    kind: str                # CE (call) or PE (put)
    short_strike: float
    long_strike: float
    expiry: date
    lots: int
    lot_size: int
    entry_credit: float      # per unit of underlying
    open_fees: float
    status: str = "open"     # open | closed
    exit_debit: float | None = None
    close_fees: float = 0.0
    close_reason: str = ""

    @property
    def width(self) -> float:
        return abs(self.long_strike - self.short_strike)

    @property
    def units(self) -> int:
        return self.lots * self.lot_size

    @property
    def max_loss(self) -> float:
        """Worst-case rupee loss (excl. fees), reserved as margin."""
        return (self.width - self.entry_credit) * self.units

    def value_to_close(self, spot: float, iv: float, t_years: float, r: float) -> float:
        """Current per-unit debit to buy the spread back."""
        kind = "call" if self.kind == "CE" else "put"
        t = max(t_years, 0.0)
        short_px = bs_price(spot, self.short_strike, t, r, iv, kind)
        long_px = bs_price(spot, self.long_strike, t, r, iv, kind)
        return max(0.0, short_px - long_px)

    def intrinsic_at(self, spot: float) -> float:
        """Per-unit settlement debit at expiry."""
        if self.kind == "CE":
            short_in = max(spot - self.short_strike, 0.0)
            long_in = max(spot - self.long_strike, 0.0)
        else:
            short_in = max(self.short_strike - spot, 0.0)
            long_in = max(self.long_strike - spot, 0.0)
        return short_in - long_in

    def realized(self) -> float:
        """Rupee P&L after close (0 while open)."""
        if self.status != "closed" or self.exit_debit is None:
            return 0.0
        return (self.entry_credit - self.exit_debit) * self.units - self.open_fees - self.close_fees


class OptionsPaperBook:
    """Defined-risk options book with margin reservation."""

    def __init__(self, capital: float, fee_per_order: float = 25.0) -> None:
        if capital <= 0:
            raise ValueError("capital must be positive")
        self.capital = capital
        self.fee_per_order = fee_per_order
        self.spreads: list[CreditSpread] = []
        self._ids = itertools.count(1)

    # --- lifecycle -------------------------------------------------------------
    def open_spread(
        self,
        symbol: str,
        kind: str,
        short_strike: float,
        long_strike: float,
        expiry: date,
        lots: int,
        lot_size: int,
        entry_credit: float,
    ) -> CreditSpread:
        if kind not in _KINDS:
            raise ValueError(f"kind must be CE or PE, got {kind!r}")
        if lots < 1 or lot_size < 1:
            raise ValueError("lots and lot_size must be >= 1")
        if entry_credit <= 0:
            raise ValueError("entry_credit must be positive (this is a CREDIT spread)")
        width = abs(long_strike - short_strike)
        if width <= 0:
            raise ValueError("strikes must differ")
        if entry_credit >= width:
            raise ValueError("credit >= width would mean riskless arbitrage; reject")
        # Correct side: a call spread's wing is ABOVE the short strike,
        # a put spread's wing BELOW.
        if kind == "CE" and long_strike <= short_strike:
            raise ValueError("CE credit spread needs long_strike > short_strike")
        if kind == "PE" and long_strike >= short_strike:
            raise ValueError("PE credit spread needs long_strike < short_strike")

        spread = CreditSpread(
            spread_id=next(self._ids),
            symbol=symbol, kind=kind,
            short_strike=short_strike, long_strike=long_strike,
            expiry=expiry, lots=lots, lot_size=lot_size,
            entry_credit=entry_credit, open_fees=self.fee_per_order,
        )
        if spread.max_loss + self.margin_reserved() > self.capital:
            raise ValueError(
                f"margin {spread.max_loss:.0f} exceeds free capital "
                f"{self.capital - self.margin_reserved():.0f}"
            )
        self.spreads.append(spread)
        return spread

    def close_spread(self, spread_id: int, exit_debit: float, reason: str) -> CreditSpread:
        spread = self._find_open(spread_id)
        spread.exit_debit = max(0.0, exit_debit)
        spread.close_fees = self.fee_per_order
        spread.status = "closed"
        spread.close_reason = reason
        return spread

    def settle_expired(self, spot: float, today: date) -> list[CreditSpread]:
        """Settle every open spread at or past expiry at intrinsic value."""
        settled = []
        for spread in self.open_spreads():
            if today >= spread.expiry:
                spread.exit_debit = spread.intrinsic_at(spot)
                spread.close_fees = 0.0  # expiry settlement, no closing order
                spread.status = "closed"
                spread.close_reason = "expiry"
                settled.append(spread)
        return settled

    # --- accounting ---------------------------------------------------------------
    def open_spreads(self) -> list[CreditSpread]:
        return [s for s in self.spreads if s.status == "open"]

    def margin_reserved(self) -> float:
        return sum(s.max_loss for s in self.open_spreads())

    def realized_pnl(self) -> float:
        return sum(s.realized() for s in self.spreads)

    def unrealized_pnl(self, spot: float, iv: float, t_years: float, r: float = 0.065) -> float:
        return sum(
            (s.entry_credit - s.value_to_close(spot, iv, t_years, r)) * s.units - s.open_fees
            for s in self.open_spreads()
        )

    def equity(self, spot: float, iv: float, t_years: float, r: float = 0.065) -> float:
        return self.capital + self.realized_pnl() + self.unrealized_pnl(spot, iv, t_years, r)

    def stats(self, spot: float | None = None, iv: float | None = None, t_years: float = 0.0) -> dict:
        out = {
            "capital": self.capital,
            "open_positions": len(self.open_spreads()),
            "margin_reserved": round(self.margin_reserved(), 2),
            "realized_pnl": round(self.realized_pnl(), 2),
            "closed_trades": sum(1 for s in self.spreads if s.status == "closed"),
        }
        if spot is not None and iv is not None:
            out["unrealized_pnl"] = round(self.unrealized_pnl(spot, iv, t_years), 2)
            out["equity"] = round(self.equity(spot, iv, t_years), 2)
        return out

    def _find_open(self, spread_id: int) -> CreditSpread:
        for s in self.open_spreads():
            if s.spread_id == spread_id:
                return s
        raise KeyError(f"no open spread {spread_id}")

    # --- restart-safe persistence -------------------------------------------
    def export_state(self) -> dict:
        """JSON-serializable snapshot of the whole book (for KvState)."""
        return {"spreads": [_spread_to_dict(s) for s in self.spreads]}

    def load_state(self, data: dict) -> None:
        """Rehydrate spreads from ``export_state`` output; resets the id counter
        past the highest restored id so new spreads never collide."""
        spreads = [_spread_from_dict(d) for d in (data or {}).get("spreads", [])]
        self.spreads = spreads
        max_id = max((s.spread_id for s in spreads), default=0)
        self._ids = itertools.count(max_id + 1)


def _spread_to_dict(s: CreditSpread) -> dict:
    return {
        "spread_id": s.spread_id, "symbol": s.symbol, "kind": s.kind,
        "short_strike": s.short_strike, "long_strike": s.long_strike,
        "expiry": s.expiry.isoformat(), "lots": s.lots, "lot_size": s.lot_size,
        "entry_credit": s.entry_credit, "open_fees": s.open_fees,
        "status": s.status, "exit_debit": s.exit_debit,
        "close_fees": s.close_fees, "close_reason": s.close_reason,
    }


def _spread_from_dict(d: dict) -> CreditSpread:
    return CreditSpread(
        spread_id=int(d["spread_id"]), symbol=d["symbol"], kind=d["kind"],
        short_strike=float(d["short_strike"]), long_strike=float(d["long_strike"]),
        expiry=date.fromisoformat(d["expiry"]), lots=int(d["lots"]),
        lot_size=int(d["lot_size"]), entry_credit=float(d["entry_credit"]),
        open_fees=float(d.get("open_fees", 0.0)), status=d.get("status", "open"),
        exit_debit=(None if d.get("exit_debit") is None else float(d["exit_debit"])),
        close_fees=float(d.get("close_fees", 0.0)), close_reason=d.get("close_reason", ""),
    )
