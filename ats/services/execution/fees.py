"""Approximate Indian equity transaction charges.

A simplified model of Zerodha-style charges so paper PnL reflects real-world
frictions (brokerage, STT, exchange txn, GST, SEBI, stamp duty). Tuned for
delivery-style cash equity; good enough for paper realism, not for tax filing.
"""

from __future__ import annotations

from dataclasses import dataclass

BROKERAGE_RATE = 0.0003       # 0.03%
BROKERAGE_CAP = 20.0          # Rs 20 per order
STT_SELL_RATE = 0.001         # 0.1% on sell (delivery)
EXCHANGE_TXN_RATE = 0.0000345 # NSE
GST_RATE = 0.18               # on (brokerage + exchange txn)
SEBI_RATE = 0.000001          # Rs 10 per crore
STAMP_BUY_RATE = 0.00015      # 0.015% on buy


@dataclass
class Charges:
    brokerage: float
    stt: float
    exchange_txn: float
    gst: float
    sebi: float
    stamp: float

    @property
    def total(self) -> float:
        return round(
            self.brokerage + self.stt + self.exchange_txn
            + self.gst + self.sebi + self.stamp,
            2,
        )


def compute_charges(side: str, qty: int, price: float) -> Charges:
    turnover = abs(qty) * price
    brokerage = min(BROKERAGE_RATE * turnover, BROKERAGE_CAP)
    is_sell = side.upper() == "SELL"
    is_buy = side.upper() == "BUY"
    stt = STT_SELL_RATE * turnover if is_sell else 0.0
    exchange_txn = EXCHANGE_TXN_RATE * turnover
    gst = GST_RATE * (brokerage + exchange_txn)
    sebi = SEBI_RATE * turnover
    stamp = STAMP_BUY_RATE * turnover if is_buy else 0.0
    return Charges(brokerage, stt, exchange_txn, gst, sebi, stamp)


def cost_fraction(side: str) -> float:
    """Per-side transaction cost as a *fraction of turnover* — the same charge
    stack as ``compute_charges`` but expressed as a rate, for the vectorized
    backtester (which works in return/turnover space, not share lots).

    The per-order ₹20 brokerage cap can't apply without an order size, so
    brokerage is taken uncapped (``BROKERAGE_RATE``): exact for the small
    per-name slices a diversified sleeve trades, and conservative (a slight
    over-estimate) for very large single orders where the cap would bite."""
    is_sell = side.upper() == "SELL"
    is_buy = side.upper() == "BUY"
    brokerage = BROKERAGE_RATE
    stt = STT_SELL_RATE if is_sell else 0.0
    exchange_txn = EXCHANGE_TXN_RATE
    gst = GST_RATE * (brokerage + exchange_txn)
    sebi = SEBI_RATE
    stamp = STAMP_BUY_RATE if is_buy else 0.0
    return brokerage + stt + exchange_txn + gst + sebi + stamp


def cost_bps(side: str) -> float:
    """Per-side cost in basis points (buy ≈ 5.5 bps, sell ≈ 14 bps — the STT on
    the sell and stamp duty on the buy are the asymmetry)."""
    return cost_fraction(side) * 10_000.0
