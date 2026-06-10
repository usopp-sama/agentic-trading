"""End-to-end demo of the quant toolkit.

Runs fully offline by default (synthetic data) so it always works:

    python scripts/demo.py

Use real market data instead (requires internet):

    python scripts/demo.py --online --ticker AAPL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python scripts/demo.py` without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from quant.analysis import indicators, valuation
from quant.analysis.screener import Screener, max_filter, min_filter
from quant.backtest import backtest_signals, crossover_signal
from quant.data import PriceStore, fetch_prices, synthetic_prices
from quant.projects import silverbees_nav
from quant.risk import fractional_kelly, kelly_from_returns, position_size


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def get_prices(online: bool, ticker: str) -> pd.DataFrame:
    if online:
        print(f"Fetching {ticker} from yfinance ...")
        return fetch_prices(ticker, period="2y")
    print("Using synthetic price data (offline).")
    return synthetic_prices(n=504, start_price=150.0, annual_drift=0.10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quant toolkit demo")
    parser.add_argument("--online", action="store_true", help="use real market data")
    parser.add_argument("--ticker", default="AAPL", help="ticker for --online mode")
    args = parser.parse_args()

    df = get_prices(args.online, args.ticker)
    close = df["close"]

    section("1. Data layer — store & reload via SQLite")
    with PriceStore(":memory:") as store:
        written = store.save_prices("DEMO", df)
        reloaded = store.load_prices("DEMO")
        print(f"Wrote {written} rows; reloaded {len(reloaded)} rows.")
        print(f"Symbols in store: {store.list_symbols()}")

    section("2. Technical indicators (latest values)")
    macd = indicators.macd(close)
    bb = indicators.bollinger_bands(close)
    print(f"Close            : {close.iloc[-1]:.2f}")
    print(f"SMA(20)          : {indicators.sma(close, 20).iloc[-1]:.2f}")
    print(f"EMA(20)          : {indicators.ema(close, 20).iloc[-1]:.2f}")
    print(f"RSI(14)          : {indicators.rsi(close, 14).iloc[-1]:.1f}")
    print(f"MACD / signal    : {macd['macd'].iloc[-1]:.3f} / {macd['signal'].iloc[-1]:.3f}")
    print(f"Bollinger %B     : {bb['pct_b'].iloc[-1]:.2f}")
    print(f"Annualized vol   : {indicators.annualized_volatility(close) * 100:.1f}%")

    section("3. Valuation — two-stage DCF")
    dcf = valuation.discounted_cash_flow(
        base_fcf=1_000_000_000,
        growth_rate=0.10,
        discount_rate=0.09,
        terminal_growth=0.025,
        years=5,
        net_debt=2_000_000_000,
        shares_outstanding=500_000_000,
    )
    print(dcf.summary())
    mos = valuation.margin_of_safety(dcf.per_share_value, market_price=20.0)
    print(f"Margin of safety vs price 20.00: {mos * 100:+.1f}%")

    section("4. Screener — value + quality filters")
    universe = pd.DataFrame(
        {
            "pe": [12.0, 35.0, 18.0, 9.0, 27.0],
            "roe": [0.22, 0.10, 0.16, 0.28, 0.08],
            "debt_to_equity": [0.3, 1.2, 0.6, 0.2, 0.9],
        },
        index=["AAA", "BBB", "CCC", "DDD", "EEE"],
    )
    screener = Screener(filters=[max_filter("pe", 20), min_filter("roe", 0.15)])
    picks = screener.run(universe, rank_by="roe", ascending=False)
    print("Passing names (ranked by ROE):")
    print(picks.to_string())

    section("5. Backtest — SMA(20/50) crossover")
    signal = crossover_signal(close, 20, 50)
    result = backtest_signals(close, signal, fee_bps=1.0)
    print(result.summary())

    section("6. Risk — Kelly position sizing")
    full_kelly = kelly_from_returns(result.returns)
    half_kelly = fractional_kelly(full_kelly, 0.5)
    shares = position_size(capital=100_000, fraction=half_kelly, price=close.iloc[-1])
    print(f"Full Kelly fraction : {full_kelly:+.3f}")
    print(f"Half Kelly fraction : {half_kelly:+.3f}")
    print(f"Shares on 100k cap. : {shares} (capped at 25% of capital)")

    section("7. Project — SILVERBEES NAV premium/discount")
    sb = silverbees_nav.run(offline=not args.online)
    print(f"Latest premium/discount : {sb['latest_premium_pct']:+.2f}%")
    print(f"Mean premium/discount   : {sb['mean_premium_pct']:+.2f}%")
    print(f"Verdict                 : {sb['verdict']}")

    print("\nDone. All modules ran end-to-end.")


if __name__ == "__main__":
    main()
