import numpy as np
import pandas as pd
import pytest

from quant.backtest import backtest_signals, crossover_signal
from quant.data.fetch import synthetic_prices
from quant.risk import kelly_fraction, position_size


@pytest.fixture
def close() -> pd.Series:
    return synthetic_prices(n=300, seed=11)["close"]


def test_buy_and_hold_matches_price_return(close):
    # A constant full-long position with no fees should match the
    # asset's own return (modulo the one-bar warm-up shift).
    pos = pd.Series(1.0, index=close.index)
    result = backtest_signals(close, pos, fee_bps=0.0)
    # The day-0 signal is applied at bar 1, so the position is long from
    # the first return onward -> total return tracks close[-1]/close[0].
    expected = close.iloc[-1] / close.iloc[0] - 1.0
    assert result.total_return == pytest.approx(expected, rel=1e-6)


def test_no_lookahead_flat_first_bar(close):
    pos = pd.Series(1.0, index=close.index)
    result = backtest_signals(close, pos, fee_bps=0.0)
    # First effective return must be zero (signal shifted by one bar).
    assert result.returns.iloc[0] == pytest.approx(0.0)


def test_fees_reduce_return(close):
    pos = crossover_signal(close, 10, 30)
    no_fee = backtest_signals(close, pos, fee_bps=0.0)
    with_fee = backtest_signals(close, pos, fee_bps=10.0)
    assert with_fee.total_return <= no_fee.total_return


def test_drawdown_is_non_positive(close):
    pos = crossover_signal(close, 10, 30)
    result = backtest_signals(close, pos)
    assert result.max_drawdown <= 0.0


def test_kelly_fraction_even_odds():
    # 60% win prob at 1:1 payoff -> bet 20%.
    assert kelly_fraction(0.60, 1.0) == pytest.approx(0.20)


def test_kelly_negative_when_unfavorable():
    assert kelly_fraction(0.40, 1.0) < 0


def test_position_size_caps_exposure():
    # Aggressive fraction should be clamped to max_fraction (25%).
    shares = position_size(capital=100_000, fraction=0.9, price=100.0, max_fraction=0.25)
    assert shares == 250  # 25% of 100k / 100


def test_position_size_floors_to_whole_shares():
    shares = position_size(capital=1_000, fraction=0.1, price=33.0)
    assert shares == 3  # floor(100 / 33)
