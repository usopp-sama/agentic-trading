"""A simple vectorized backtester.

Takes a price series and a target-position series (signals) and computes
the equity curve and a set of standard performance statistics. Signals
are shifted by one bar before being applied, so a signal generated on
bar *t* is acted on at bar *t+1* — this avoids look-ahead bias, the most
common backtesting mistake.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    total_return: float
    cagr: float
    annual_volatility: float
    sharpe: float
    max_drawdown: float
    n_trades: int

    def summary(self) -> str:
        return (
            f"Total return     : {self.total_return * 100:,.2f}%\n"
            f"CAGR             : {self.cagr * 100:,.2f}%\n"
            f"Annual vol       : {self.annual_volatility * 100:,.2f}%\n"
            f"Sharpe           : {self.sharpe:,.2f}\n"
            f"Max drawdown     : {self.max_drawdown * 100:,.2f}%\n"
            f"Trades           : {self.n_trades}"
        )


def backtest_signals(
    prices: pd.Series,
    target_position: pd.Series,
    fee_bps: float = 1.0,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> BacktestResult:
    """Backtest a target-position series against prices.

    Parameters
    ----------
    prices:
        Price series (close).
    target_position:
        Desired exposure per bar, typically in ``{-1, 0, 1}`` (short, flat,
        long) but any float weight works. Aligned to ``prices``.
    fee_bps:
        Round-trip-agnostic transaction cost in basis points, charged on
        the *change* in position each bar.
    periods_per_year:
        252 for daily bars, 12 for monthly, etc.
    risk_free_rate:
        Annual risk-free rate used in the Sharpe ratio.
    """
    prices = prices.dropna()
    pos = target_position.reindex(prices.index).ffill().fillna(0.0)

    # Act on yesterday's signal -> no look-ahead.
    pos_eff = pos.shift(1).fillna(0.0)

    asset_ret = prices.pct_change().fillna(0.0)
    gross = pos_eff * asset_ret

    turnover = pos_eff.diff().abs().fillna(pos_eff.abs())
    cost = turnover * (fee_bps / 10_000.0)
    net = gross - cost

    equity = (1.0 + net).cumprod()
    n_periods = len(net)

    total_return = float(equity.iloc[-1] - 1.0) if n_periods else 0.0
    years = n_periods / periods_per_year if periods_per_year else 0.0
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0

    ann_vol = float(net.std(ddof=1) * np.sqrt(periods_per_year)) if n_periods > 1 else 0.0
    excess = net.mean() * periods_per_year - risk_free_rate
    sharpe = float(excess / ann_vol) if ann_vol > 0 else 0.0

    max_dd = _max_drawdown(equity)
    n_trades = int((pos_eff.diff().abs() > 1e-9).sum())

    return BacktestResult(
        equity_curve=equity,
        returns=net,
        total_return=total_return,
        cagr=cagr,
        annual_volatility=ann_vol,
        sharpe=sharpe,
        max_drawdown=max_dd,
        n_trades=n_trades,
    )


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def crossover_signal(
    prices: pd.Series,
    fast_window: int = 20,
    slow_window: int = 50,
) -> pd.Series:
    """Long when fast SMA > slow SMA, else flat. A classic baseline."""
    from quant.analysis.indicators import sma

    fast = sma(prices, fast_window)
    slow = sma(prices, slow_window)
    return (fast > slow).astype(float)
