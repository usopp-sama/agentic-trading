"""First mini-project: SILVERBEES NAV premium/discount analysis.

SILVERBEES (Nippon India Silver ETF, ``SILVERBEES.NS``) trades on the
NSE. Its market price can drift above or below the value of the silver it
holds (its NAV). This script pulls the price history, derives a proxy
NAV, and reports when the ETF historically traded at a premium vs a
discount — the core idea being "buy at a discount, avoid at a premium".

NAV note
--------
Official end-of-day NAV is published by the AMC, not by yfinance. For a
learning project we approximate NAV from the underlying silver price
(``SI=F`` silver futures) scaled to the ETF's units. You can later swap
``approx_nav_from_silver`` for the real AMC NAV feed without changing the
analysis code.
"""

from __future__ import annotations

import pandas as pd

from quant.analysis.valuation import nav_premium_discount
from quant.data.fetch import fetch_prices, synthetic_prices


def approx_nav_from_silver(
    etf_close: pd.Series,
    silver_close: pd.Series,
) -> pd.Series:
    """Build a proxy NAV by scaling silver price to the ETF's level.

    We anchor the proxy so that, on the first common date, NAV equals the
    ETF close. Subsequent NAV moves track the silver price. This is a
    teaching approximation, not the official NAV.
    """
    df = pd.DataFrame({"etf": etf_close, "silver": silver_close}).dropna()
    if df.empty:
        raise ValueError("No overlapping dates between ETF and silver series")
    scale = df["etf"].iloc[0] / df["silver"].iloc[0]
    return (df["silver"] * scale).rename("nav")


def analyze(
    etf_prices: pd.Series,
    nav: pd.Series,
    premium_threshold: float = 1.0,
) -> dict:
    """Compute premium/discount stats and a simple current verdict."""
    table = nav_premium_discount(etf_prices, nav)
    prem = table["premium_pct"]
    latest = prem.iloc[-1]

    if latest <= -premium_threshold:
        verdict = "DISCOUNT — historically a more attractive entry"
    elif latest >= premium_threshold:
        verdict = "PREMIUM — paying above NAV, be cautious"
    else:
        verdict = "FAIR — within +/- {:.1f}% of NAV".format(premium_threshold)

    return {
        "table": table,
        "latest_premium_pct": float(latest),
        "mean_premium_pct": float(prem.mean()),
        "std_premium_pct": float(prem.std(ddof=1)),
        "pct_days_at_premium": float((prem > 0).mean() * 100.0),
        "verdict": verdict,
    }


def run(offline: bool = False) -> dict:
    """Run the full analysis. Falls back to synthetic data when offline."""
    if offline:
        etf = synthetic_prices(n=252, start_price=95.0, seed=1)["close"]
        silver = synthetic_prices(n=252, start_price=30.0, seed=2)["close"]
        nav = approx_nav_from_silver(etf, silver)
        return analyze(etf, nav)

    try:
        etf = fetch_prices("SILVERBEES.NS", period="1y")["close"]
        silver = fetch_prices("SI=F", period="1y")["close"]
    except RuntimeError as exc:
        raise RuntimeError(
            f"{exc}\nTip: re-run with offline=True to use synthetic data."
        ) from exc

    nav = approx_nav_from_silver(etf, silver)
    return analyze(etf, nav)


def _print_report(result: dict) -> None:
    print("SILVERBEES NAV Premium/Discount Analysis")
    print("=" * 44)
    print(f"Latest premium/discount : {result['latest_premium_pct']:+.2f}%")
    print(f"Mean premium/discount   : {result['mean_premium_pct']:+.2f}%")
    print(f"Std deviation           : {result['std_premium_pct']:.2f}%")
    print(f"Days trading at premium : {result['pct_days_at_premium']:.1f}%")
    print(f"Verdict                 : {result['verdict']}")


if __name__ == "__main__":
    import sys

    use_offline = "--offline" in sys.argv
    try:
        _print_report(run(offline=use_offline))
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)
