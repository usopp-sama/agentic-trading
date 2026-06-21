"""Strategy backtest harness + shadow->paper promotion gate.

The live ``Strategy``/``UniverseStrategy`` classes emit a *stance* per bar, not
the target-position series the vectorized ``quant.backtest`` engine consumes.
This module bridges the two by replaying each strategy bar-by-bar over a price
panel (look-ahead safe — the stance decided on bar *t* is acted on at *t+1*),
building an equal-weight long-only return series for the strategy's virtual
sleeve, then scoring it with the anti-overfit statistics in
``quant.backtest.validation``:

- annualized Sharpe on the stitched return series,
- the **deflated Sharpe ratio** (Bailey & Lopez de Prado, 2014) with
  ``n_trials`` = number of strategies tested, which discounts the best result
  for the multiple-testing search that produced it, and
- block-bootstrap **Monte Carlo drawdowns** to size tail risk.

A strategy clears the promotion gate (shadow -> paper) only when it has enough
observations AND its deflated Sharpe beats the configured bar AND its raw Sharpe
is positive — mirroring the SME ``promotion_decision`` pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ats.core.schemas import Stance
from ats.services.strategies.base import Strategy, UniverseStrategy
from quant.backtest.engine import backtest_signals
from quant.backtest.validation import deflated_sharpe_ratio, monte_carlo_drawdowns


@dataclass
class GateResult:
    strategy: str
    n_obs: int
    sharpe: float
    total_return: float
    max_drawdown: float
    deflated_sharpe: float
    mc_dd_p95: float | None
    passes: bool
    reason: str = ""


@dataclass
class GateReport:
    results: list[GateResult] = field(default_factory=list)

    def promote_ids(self) -> list[str]:
        return [r.strategy for r in self.results if r.passes]

    def summary(self) -> str:
        lines = [f"{'strategy':22} {'n':>4} {'sharpe':>7} {'dsr':>6} {'dd95':>7}  verdict"]
        for r in sorted(self.results, key=lambda x: x.deflated_sharpe, reverse=True):
            dd = f"{r.mc_dd_p95:.2%}" if r.mc_dd_p95 is not None else "   n/a"
            verdict = "PROMOTE" if r.passes else f"hold ({r.reason})"
            lines.append(
                f"{r.strategy:22} {r.n_obs:>4} {r.sharpe:>7.2f} "
                f"{r.deflated_sharpe:>6.2f} {dd:>7}  {verdict}"
            )
        return "\n".join(lines)


def _stance_position(stance: Stance) -> float:
    # Long-only paper sleeves: bullish = held, everything else = flat.
    return 1.0 if stance == Stance.BUY else 0.0


def replay_per_symbol(
    strategy: Strategy, panel: dict[str, pd.DataFrame], step: int = 1
) -> pd.DataFrame:
    """Replay a per-symbol strategy; return a (date x symbol) position frame."""
    positions: dict[str, pd.Series] = {}
    for sym, df in panel.items():
        n = len(df)
        warmup = min(getattr(strategy, "min_bars", 60), n)
        pos = pd.Series(0.0, index=df.index)
        last = 0.0
        for t in range(warmup, n + 1):
            if (t - warmup) % step != 0 and t != n:
                pos.iloc[t - 1] = last
                continue
            window = df.iloc[:t]
            try:
                sig = strategy.evaluate(sym, window)
            except Exception:  # noqa: BLE001 - a single bad bar must not abort the run
                sig = None
            if sig is not None and sig.stance != Stance.NEUTRAL:
                last = _stance_position(sig.stance)
            elif sig is not None and sig.stance == Stance.NEUTRAL:
                last = 0.0
            pos.iloc[t - 1] = last
        positions[sym] = pos
    if not positions:
        return pd.DataFrame()
    return pd.DataFrame(positions)


def replay_universe(
    strategy: UniverseStrategy, panel: dict[str, pd.DataFrame], step: int = 5
) -> pd.DataFrame:
    """Replay a universe strategy; return a (date x symbol) position frame."""
    if not panel:
        return pd.DataFrame()
    index = sorted({ts for df in panel.values() for ts in df.index})
    cols = list(panel.keys())
    pos = pd.DataFrame(0.0, index=pd.DatetimeIndex(index), columns=cols)
    warmup = min(getattr(strategy, "min_bars", 60), len(index))
    held: set[str] = set()
    for i in range(warmup, len(index)):
        ts = index[i]
        if (i - warmup) % step == 0:
            hist = {s: df.loc[:ts] for s, df in panel.items() if not df.loc[:ts].empty}
            try:
                signals = strategy.evaluate_universe(hist)
            except Exception:  # noqa: BLE001
                signals = []
            for sig in signals:
                if sig.stance == Stance.BUY:
                    held.add(sig.symbol)
                elif sig.stance in (Stance.SELL, Stance.NEUTRAL):
                    held.discard(sig.symbol)
        for sym in held:
            if sym in pos.columns:
                pos.at[ts, sym] = 1.0
    return pos


def portfolio_returns(
    positions: pd.DataFrame, panel: dict[str, pd.DataFrame], fee_bps: float = 5.0
) -> pd.Series:
    """Equal-weight long-only return of the held basket, fees on turnover.

    Each held name contributes its own (look-ahead-safe) net return; the daily
    portfolio return is the average across names held that day, matching the
    equal-weight virtual sleeve the live ``SleeveTracker`` keeps.
    """
    if positions.empty:
        return pd.Series(dtype=float)
    per_symbol = []
    for sym in positions.columns:
        df = panel.get(sym)
        if df is None or df.empty:
            continue
        prices = df["close"]
        pos = positions[sym].reindex(prices.index).ffill().fillna(0.0)
        res = backtest_signals(prices, pos, fee_bps=fee_bps)
        per_symbol.append(res.returns.rename(sym))
    if not per_symbol:
        return pd.Series(dtype=float)
    ret_frame = pd.concat(per_symbol, axis=1)
    pos_frame = positions.reindex(ret_frame.index).shift(1).fillna(0.0)
    # Average only across names actually held that day; 0 when flat.
    masked = ret_frame.where(pos_frame > 0)
    daily = masked.mean(axis=1, skipna=True).fillna(0.0)
    return daily


def evaluate_strategy(
    strategy_id: str, returns: pd.Series, n_trials: int,
    dsr_threshold: float, min_obs: int,
) -> GateResult:
    """Score a strategy's return series and apply the promotion gate."""
    rets = returns.dropna()
    n = int((rets != 0).sum())  # active observations
    if len(rets) < 2 or n < min_obs:
        return GateResult(strategy_id, n, 0.0, 0.0, 0.0, 0.0, None, False,
                          reason=f"only {n} active obs (<{min_obs})")
    equity = (1.0 + rets).cumprod()
    res = backtest_signals(equity, pd.Series(1.0, index=equity.index), fee_bps=0.0)
    sharpe = res.sharpe
    skew = float(rets.skew()) if len(rets) > 2 else 0.0
    kurt = float(rets.kurtosis() + 3.0) if len(rets) > 3 else 3.0
    try:
        dsr = deflated_sharpe_ratio(sharpe, n_trials=max(1, n_trials),
                                    n_obs=len(rets), skew=skew, kurtosis=kurt)
    except Exception:  # noqa: BLE001
        dsr = 0.0
    mc_dd = None
    try:
        mc = monte_carlo_drawdowns(rets)
        mc_dd = mc["dd_p95"]
    except Exception:  # noqa: BLE001
        mc_dd = None
    passes = sharpe > 0 and dsr >= dsr_threshold and n >= min_obs
    reason = "" if passes else (
        "sharpe<=0" if sharpe <= 0 else f"dsr {dsr:.2f}<{dsr_threshold}"
    )
    return GateResult(strategy_id, n, round(sharpe, 3), round(res.total_return, 4),
                      round(res.max_drawdown, 4), round(dsr, 3),
                      round(mc_dd, 4) if mc_dd is not None else None, passes, reason)


def run_gate(
    panel: dict[str, pd.DataFrame],
    per_symbol_strategies: list[Strategy],
    universe_strategies: list[UniverseStrategy],
    dsr_threshold: float = 0.90,
    min_obs: int = 30,
    fee_bps: float = 5.0,
    step: int = 1,
    universe_step: int = 5,
) -> GateReport:
    """Backtest every strategy over ``panel`` and apply the promotion gate."""
    n_trials = len(per_symbol_strategies) + len(universe_strategies)
    report = GateReport()
    for strat in per_symbol_strategies:
        positions = replay_per_symbol(strat, panel, step=step)
        rets = portfolio_returns(positions, panel, fee_bps=fee_bps)
        report.results.append(
            evaluate_strategy(strat.id, rets, n_trials, dsr_threshold, min_obs)
        )
    for strat in universe_strategies:
        symbols = strat.symbols() or list(panel.keys())
        sub_panel = {s: panel[s] for s in symbols if s in panel}
        positions = replay_universe(strat, sub_panel, step=universe_step)
        rets = portfolio_returns(positions, sub_panel, fee_bps=fee_bps)
        report.results.append(
            evaluate_strategy(strat.id, rets, n_trials, dsr_threshold, min_obs)
        )
    return report
