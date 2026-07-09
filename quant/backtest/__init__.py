"""Backtesting and backtest-hygiene validation."""

from quant.backtest.engine import (
    BacktestResult,
    backtest_signals,
    crossover_signal,
)
from quant.backtest.validation import (
    WalkForwardResult,
    deflated_sharpe_ratio,
    grid_search,
    monte_carlo_drawdowns,
    plateau_ratio,
    walk_forward,
    walk_forward_splits,
)

__all__ = [
    "BacktestResult",
    "backtest_signals",
    "crossover_signal",
    "WalkForwardResult",
    "walk_forward",
    "walk_forward_splits",
    "grid_search",
    "monte_carlo_drawdowns",
    "plateau_ratio",
    "deflated_sharpe_ratio",
]
