"""Fundamental valuation tools.

Covers the intrinsic-value methods from the roadmap:

- Discounted Cash Flow (DCF) for stocks
- Dividend Discount Model (Gordon growth)
- Relative valuation helpers (margin of safety)
- ETF NAV premium / discount
- Cost-of-carry fair futures price for commodities
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class DCFResult:
    enterprise_value: float
    equity_value: float
    per_share_value: float
    pv_explicit: float
    pv_terminal: float
    projected_fcf: list[float] = field(default_factory=list)
    discounted_fcf: list[float] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Enterprise value : {self.enterprise_value:,.0f}\n"
            f"Equity value     : {self.equity_value:,.0f}\n"
            f"Per-share value  : {self.per_share_value:,.2f}\n"
            f"PV (explicit)    : {self.pv_explicit:,.0f}\n"
            f"PV (terminal)    : {self.pv_terminal:,.0f}"
        )


def discounted_cash_flow(
    base_fcf: float,
    growth_rate: float,
    discount_rate: float,
    terminal_growth: float,
    years: int = 5,
    net_debt: float = 0.0,
    shares_outstanding: float | None = None,
) -> DCFResult:
    """Two-stage DCF valuation.

    Parameters
    ----------
    base_fcf:
        Most recent free cash flow (the year-0 figure to grow from).
    growth_rate:
        Annual FCF growth during the explicit forecast period (e.g. 0.10).
    discount_rate:
        WACC / required return (e.g. 0.09). Must exceed ``terminal_growth``.
    terminal_growth:
        Perpetual growth rate after the explicit period (e.g. 0.025).
    years:
        Length of the explicit forecast period.
    net_debt:
        Debt minus cash; subtracted from enterprise value to get equity value.
    shares_outstanding:
        If provided, per-share value is computed.
    """
    if years < 1:
        raise ValueError("years must be >= 1")
    if discount_rate <= terminal_growth:
        raise ValueError(
            "discount_rate must exceed terminal_growth for a finite "
            f"terminal value (got r={discount_rate}, g={terminal_growth})"
        )

    projected_fcf: list[float] = []
    discounted_fcf: list[float] = []
    fcf = base_fcf
    for year in range(1, years + 1):
        fcf = fcf * (1.0 + growth_rate)
        projected_fcf.append(fcf)
        discounted_fcf.append(fcf / (1.0 + discount_rate) ** year)

    pv_explicit = float(np.sum(discounted_fcf))

    # Terminal value via Gordon growth on the final-year FCF.
    terminal_fcf = projected_fcf[-1] * (1.0 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1.0 + discount_rate) ** years

    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - net_debt
    per_share = (
        equity_value / shares_outstanding
        if shares_outstanding
        else float("nan")
    )

    return DCFResult(
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        per_share_value=per_share,
        pv_explicit=pv_explicit,
        pv_terminal=pv_terminal,
        projected_fcf=projected_fcf,
        discounted_fcf=discounted_fcf,
    )


def dividend_discount_model(
    dividend_next_year: float,
    required_return: float,
    growth_rate: float,
) -> float:
    """Gordon growth model: V = D1 / (r - g)."""
    if required_return <= growth_rate:
        raise ValueError("required_return must exceed growth_rate")
    return dividend_next_year / (required_return - growth_rate)


def margin_of_safety(intrinsic_value: float, market_price: float) -> float:
    """Fractional discount of price to intrinsic value.

    Positive means the price is below intrinsic value (a margin of
    safety exists); negative means it trades at a premium.
    """
    if intrinsic_value <= 0:
        raise ValueError("intrinsic_value must be positive")
    return (intrinsic_value - market_price) / intrinsic_value


def nav_premium_discount(
    market_price: pd.Series,
    nav: pd.Series,
) -> pd.DataFrame:
    """ETF premium/discount to NAV.

    Returns a DataFrame with ``market_price``, ``nav`` and ``premium_pct``
    (positive = trading at a premium, negative = at a discount).
    """
    aligned = pd.DataFrame({"market_price": market_price, "nav": nav}).dropna()
    aligned["premium_pct"] = (
        (aligned["market_price"] - aligned["nav"]) / aligned["nav"] * 100.0
    )
    return aligned


def fair_futures_price(
    spot: float,
    risk_free_rate: float,
    storage_cost: float,
    convenience_yield: float,
    time_to_expiry_years: float,
) -> float:
    """Cost-of-carry fair futures price for a commodity.

    F = S * exp((r + storage - convenience) * T)

    Rates are continuously compounded annual fractions.
    """
    if time_to_expiry_years < 0:
        raise ValueError("time_to_expiry_years must be non-negative")
    carry = risk_free_rate + storage_cost - convenience_yield
    return float(spot * np.exp(carry * time_to_expiry_years))


def pe_ratio(price: float, earnings_per_share: float) -> float:
    if earnings_per_share == 0:
        return float("nan")
    return price / earnings_per_share


def peg_ratio(pe: float, earnings_growth_pct: float) -> float:
    if earnings_growth_pct == 0:
        return float("nan")
    return pe / earnings_growth_pct
