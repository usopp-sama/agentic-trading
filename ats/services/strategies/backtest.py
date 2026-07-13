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
from typing import Callable

import numpy as np
import pandas as pd

from ats.core.schemas import Stance
from ats.services.strategies.base import Strategy, UniverseStrategy
from quant.backtest.engine import backtest_signals
from quant.backtest.validation import (
    deflated_sharpe_ratio,
    grid_search,
    monte_carlo_drawdowns,
    plateau_ratio,
)

# Notional starting capital used only to translate a strategy's return series
# into a plain-rupee "made / lost this much" figure for the human-readable
# report. It does NOT affect any statistic (Sharpe/DSR are scale-free).
NOTIONAL_INR = 100_000.0

# Below this plateau ratio, a tunable strategy's best parameters sit on a spike
# rather than a robust plateau — a curve-fit warning (E2). Diagnostic only.
PLATEAU_MIN = 0.6


def format_inr(x: float) -> str:
    """Rupees with Indian digit grouping and an ASCII ``Rs`` prefix (never the
    ₹ glyph — the Windows console is cp1252 and would crash on it)."""
    n = int(round(x))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        grouped = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        parts.insert(0, head)
        grouped = ",".join(parts) + "," + tail
    return f"Rs {sign}{grouped}"


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
    # --- plain-English extras (for a non-quant reader; no effect on scoring) ---
    trades: int = 0            # number of times the strategy opened a position
    symbols_traded: int = 0    # distinct stocks it ever held
    profit_inr: float = 0.0    # P&L on NOTIONAL_INR of notional capital
    win_rate: float = 0.0      # share of active days that were positive
    long_short: bool = False   # scored with shorts (True) or long-only (False)
    data_gap: bool = False     # n=0 because there was no data, not a real result
    # --- walk-forward (E2): Sharpe on the held-out later part of the history ---
    oos_sharpe: float | None = None   # None unless walk-forward evaluation ran
    oos_windows: int = 0
    # --- parameter robustness (E2): plateau vs curve-fit spike ---------------
    plateau_ratio: float | None = None  # None unless a tunable strategy was probed

    def is_curve_fit(self) -> bool:
        """True when the best parameters sit on a spike, not a plateau — the
        edge likely won't survive out of sample even if the DSR clears."""
        return self.plateau_ratio is not None and self.plateau_ratio < PLATEAU_MIN

    def oos_decayed(self) -> bool:
        """True when the edge weakened materially out-of-sample: full Sharpe was
        positive but the later, held-out Sharpe fell below half of it (or went
        negative). A flag to distrust the DSR even if it clears the bar."""
        if self.oos_sharpe is None or self.sharpe <= 0:
            return False
        return self.oos_sharpe < max(0.0, 0.5 * self.sharpe)

    def plain_english(self) -> str:
        """One sentence a finance-illiterate reader can follow."""
        if self.data_gap:
            return f"{self.strategy}: no data to test over this window (skipped, not judged)."
        made = "made" if self.profit_inr >= 0 else "lost"
        verdict = ("PASSED the promotion test" if self.passes
                   else "did NOT pass the promotion test")
        return (f"{self.strategy}: traded {self.symbols_traded} stock(s) over "
                f"{self.trades} trade(s), {made} {format_inr(abs(self.profit_inr))} on "
                f"{format_inr(NOTIONAL_INR)} - won {self.win_rate:.0%} of days - {verdict}.")


@dataclass
class GateReport:
    results: list[GateResult] = field(default_factory=list)

    def promote_ids(self) -> list[str]:
        return [r.strategy for r in self.results if r.passes]

    def summary(self) -> str:
        """A legible report: a plain-English headline, then a columns table.

        Columns: trades / stocks / P&L (on the notional) / win% are for human
        intuition; sharpe / dsr / dd95 are the statistics the gate actually
        decides on (dsr = deflated Sharpe, the multiple-testing-aware bar)."""
        scored = [r for r in self.results if not r.data_gap]
        gaps = [r for r in self.results if r.data_gap]
        made = [r for r in scored if r.profit_inr > 0]
        passed = [r for r in scored if r.passes]
        best = max(scored, key=lambda x: x.profit_inr, default=None)
        wf = any(r.oos_sharpe is not None for r in scored)   # walk-forward ran?
        decayed = [r for r in scored if r.oos_decayed()]
        probed = any(r.plateau_ratio is not None for r in scored)  # any tunable strat probed?
        curve_fit = [r for r in scored if r.is_curve_fit()]

        buy_c, sell_c = indian_cost_bps()
        head = [
            "=" * 88,
            "PLAIN ENGLISH",
            "-" * 88,
            f"Tested {len(scored)} strategies on {format_inr(NOTIONAL_INR)} of pretend money each.",
            f"  P&L is AFTER realistic costs (Zerodha delivery: brokerage + STT + stamp + "
            f"exchange + GST + SEBI ~ {buy_c:.1f} bps buy / {sell_c:.1f} bps sell).",
            f"  {len(made)} made money, {len(scored) - len(made)} lost money.",
        ]
        if best is not None:
            head.append(f"  Best: {best.strategy} ({format_inr(best.profit_inr)}).")
        head.append(f"  {len(passed)} cleared the promotion test "
                    f"(needs a deflated-Sharpe >= the bar AND positive returns).")
        if wf:
            head.append(f"  Walk-forward: {len(decayed)} strategies whose edge weakened "
                        f"out-of-sample (full Sharpe ok, later Sharpe fell) - marked [decay].")
        if probed:
            head.append(f"  Parameter check: {len(curve_fit)} tunable strategies whose best "
                        f"settings sit on a spike not a plateau (likely curve-fit) - marked [curve-fit].")
        if gaps:
            head.append(f"  {len(gaps)} skipped for lack of data: "
                        f"{', '.join(g.strategy for g in gaps)}.")

        oos_h = f"{'oos_sh':>7} " if wf else ""
        plat_h = f"{'plat':>5} " if probed else ""
        table = ["", "DETAIL (sorted by deflated Sharpe)", "-" * 88,
                 f"{'strategy':22} {'trades':>6} {'stocks':>6} {'P&L (1L notional)':>18} "
                 f"{'win%':>5} {'sharpe':>7} {oos_h}{plat_h}{'dsr':>6} {'dd95':>7}  verdict"]
        for r in sorted(self.results, key=lambda x: (x.data_gap, -x.deflated_sharpe)):
            if r.data_gap:
                oos_c = f"{'-':>7} " if wf else ""
                plat_c = f"{'-':>5} " if probed else ""
                table.append(f"{r.strategy:22} {'-':>6} {'-':>6} {'no data':>18} "
                             f"{'-':>5} {'-':>7} {oos_c}{plat_c}{'-':>6} {'-':>7}  skip (data gap)")
                continue
            dd = f"{r.mc_dd_p95:.2%}" if r.mc_dd_p95 is not None else "   n/a"
            oos_c = ""
            if wf:
                oos_c = (f"{r.oos_sharpe:>7.2f} " if r.oos_sharpe is not None else f"{'n/a':>7} ")
            plat_c = ""
            if probed:
                plat_c = (f"{r.plateau_ratio:>5.2f} " if r.plateau_ratio is not None else f"{'-':>5} ")
            tag = " [L/S]" if r.long_short else ""
            if r.oos_decayed():
                tag += " [decay]"
            if r.is_curve_fit():
                tag += " [curve-fit]"
            verdict = "PROMOTE" if r.passes else f"hold ({r.reason})"
            table.append(
                f"{r.strategy:22} {r.trades:>6} {r.symbols_traded:>6} "
                f"{format_inr(r.profit_inr):>18} {r.win_rate*100:>4.0f}% "
                f"{r.sharpe:>7.2f} {oos_c}{plat_c}{r.deflated_sharpe:>6.2f} {dd:>7}  {verdict}{tag}"
            )
        return "\n".join(head + table)


def _stance_position(stance: Stance, long_short: bool = False) -> float:
    """Map a stance to a target position. Long-only (default): BUY=held (1),
    everything else flat (0). Long-short (E1): BUY=+1, SELL=-1, NEUTRAL=0 — so
    inherently market-neutral sleeves (pairs/cointegration) are measured with
    their short leg intact instead of silently flattened to long-only."""
    if stance == Stance.BUY:
        return 1.0
    if long_short and stance == Stance.SELL:
        return -1.0
    return 0.0


def replay_per_symbol(
    strategy: Strategy, panel: dict[str, pd.DataFrame], step: int = 1,
    long_short: bool = False,
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
            if sig is not None:
                last = _stance_position(sig.stance, long_short=long_short)
            pos.iloc[t - 1] = last
        positions[sym] = pos
    if not positions:
        return pd.DataFrame()
    return pd.DataFrame(positions)


def replay_universe(
    strategy: UniverseStrategy, panel: dict[str, pd.DataFrame], step: int = 5,
    long_short: bool = False,
) -> pd.DataFrame:
    """Replay a universe strategy; return a (date x symbol) position frame.

    ``long_short`` keeps SELL legs as real short positions (-1) rather than
    just flattening a holding — the difference between measuring a pairs
    strategy as what it is vs. a mutilated long-only proxy."""
    if not panel:
        return pd.DataFrame()
    index = sorted({ts for df in panel.values() for ts in df.index})
    cols = list(panel.keys())
    pos = pd.DataFrame(0.0, index=pd.DatetimeIndex(index), columns=cols)
    warmup = min(getattr(strategy, "min_bars", 60), len(index))
    # symbol -> current target position; absent = flat.
    held: dict[str, float] = {}
    for i in range(warmup, len(index)):
        ts = index[i]
        if (i - warmup) % step == 0:
            hist = {s: df.loc[:ts] for s, df in panel.items() if not df.loc[:ts].empty}
            try:
                signals = strategy.evaluate_universe(hist)
            except Exception:  # noqa: BLE001
                signals = []
            for sig in signals:
                target = _stance_position(sig.stance, long_short=long_short)
                if target == 0.0:
                    held.pop(sig.symbol, None)
                else:
                    held[sig.symbol] = target
        for sym, target in held.items():
            if sym in pos.columns:
                pos.at[ts, sym] = target
    return pos


def indian_cost_bps() -> tuple[float, float]:
    """(buy_bps, sell_bps) for NSE delivery equity — the same charge stack the
    paper broker applies (brokerage + STT + exchange + GST + SEBI + stamp),
    expressed as per-side rates. Buy ≈ 5.5 bps, sell ≈ 14 bps."""
    from ats.services.execution.fees import cost_bps

    return cost_bps("BUY"), cost_bps("SELL")


def portfolio_returns(
    positions: pd.DataFrame, panel: dict[str, pd.DataFrame],
    fee_bps: float | None = None,
    buy_bps: float | None = None, sell_bps: float | None = None,
) -> pd.Series:
    """Equal-weight return of the held basket, net of realistic costs.

    Each held name contributes its own (look-ahead-safe) net return; the daily
    portfolio return is the average across names held that day, matching the
    equal-weight virtual sleeve the live ``SleeveTracker`` keeps.

    Costs default to the **Indian per-side model** (buy vs sell differ because
    STT is sell-side and stamp duty is buy-side) — the same frictions the live
    paper broker charges — so a high-churn strategy pays for its turnover. Pass
    ``fee_bps`` for a flat symmetric cost instead, or explicit ``buy_bps``/
    ``sell_bps`` to override.
    """
    if positions.empty:
        return pd.Series(dtype=float)
    if fee_bps is None and buy_bps is None and sell_bps is None:
        buy_bps, sell_bps = indian_cost_bps()
    per_symbol = []
    for sym in positions.columns:
        df = panel.get(sym)
        if df is None or df.empty:
            continue
        prices = df["close"]
        pos = positions[sym].reindex(prices.index).ffill().fillna(0.0)
        res = backtest_signals(prices, pos, fee_bps=fee_bps or 0.0,
                               buy_bps=buy_bps, sell_bps=sell_bps)
        per_symbol.append(res.returns.rename(sym))
    if not per_symbol:
        return pd.Series(dtype=float)
    ret_frame = pd.concat(per_symbol, axis=1)
    pos_frame = positions.reindex(ret_frame.index).shift(1).fillna(0.0)
    # Average across names actually held that day (long OR short); 0 when flat.
    # Each per-symbol return already carries the position's sign, so a short
    # leg's gain-on-decline is counted correctly.
    masked = ret_frame.where(pos_frame.abs() > 1e-9)
    daily = masked.mean(axis=1, skipna=True).fillna(0.0)
    return daily


def _ann_sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized Sharpe of a daily return series (0 if degenerate)."""
    r = returns.dropna()
    if len(r) < 2:
        return 0.0
    sd = float(r.std(ddof=1))
    return float(r.mean() / sd * (periods_per_year ** 0.5)) if sd > 0 else 0.0


def walk_forward_oos(returns: pd.Series, train: int = 252, test: int = 63) -> tuple[float, int]:
    """Time-based out-of-sample Sharpe (E2): hold out the first ``train`` bars as
    burn-in, then score the strategy only on the stitched *later* rolling
    ``test`` windows it never got a warm-up advantage on.

    These strategies use fixed, a-priori parameters (no per-window refitting), so
    'train' here means "the history the strategy had already seen", not a grid
    search — the point is to catch an edge that was real early then decayed while
    the full-period Sharpe still looks fine. Returns ``(oos_sharpe, n_windows)``;
    ``(0.0, 0)`` when there isn't enough history for one full window."""
    from quant.backtest.validation import walk_forward_splits

    rets = returns.dropna()
    try:
        splits = walk_forward_splits(len(rets), train, test)
    except ValueError:
        return 0.0, 0
    if not splits:
        return 0.0, 0
    stitched = pd.concat([rets.iloc[test_sl] for _, test_sl in splits])
    stitched = stitched[~stitched.index.duplicated(keep="first")]
    return round(_ann_sharpe(stitched), 3), len(splits)


def composite_series(panel: dict[str, pd.DataFrame], min_bars: int = 60) -> pd.Series:
    """An equal-weight composite 'index' of the panel: each name normalized to
    start at 1.0, then averaged. A single representative price series to grid-
    search a strategy's parameters against for the plateau/curve-fit probe (E2)."""
    norm: list[pd.Series] = []
    for df in panel.values():
        if df is None or df.empty:
            continue
        c = df["close"].dropna()
        if len(c) >= min_bars and float(c.iloc[0]) > 0:
            norm.append(c / float(c.iloc[0]))
    if not norm:
        return pd.Series(dtype=float)
    return pd.concat(norm, axis=1).mean(axis=1).dropna()


def plateau_probe(strat, prices: pd.Series, metric: str = "sharpe") -> float | None:
    """Parameter-robustness of a tunable strategy (E2). If ``strat`` opts in with
    ``param_grid()`` + ``signal_series(prices, **params)``, grid-search the metric
    over its grid on ``prices`` and return the plateau ratio (mean of the top few
    scores over the best) in [0, 1] — near 1 = robust plateau, low = curve-fit
    spike. None for strategies that don't expose the probe or when it can't run."""
    grid_fn = getattr(strat, "param_grid", None)
    sig_fn = getattr(strat, "signal_series", None)
    if grid_fn is None or sig_fn is None or prices is None or prices.empty:
        return None
    try:
        _, results = grid_search(prices, sig_fn, grid_fn(), metric=metric)
        by_param = {i: r[metric] for i, r in enumerate(results)}
        return round(plateau_ratio(by_param), 3)
    except Exception:  # noqa: BLE001 - a probe failure must never break the gate
        return None


def position_stats(positions: pd.DataFrame) -> dict:
    """Plain-English trade counters from a position frame: how many distinct
    stocks were ever held, and how many times a position was opened (a flat→
    held transition, long or short). No effect on scoring."""
    if positions is None or positions.empty:
        return {"trades": 0, "symbols_traded": 0}
    trades = 0
    symbols = 0
    for sym in positions.columns:
        held = positions[sym].fillna(0.0).abs() > 1e-9
        if bool(held.any()):
            symbols += 1
            opened = held & ~held.shift(1, fill_value=False)
            trades += int(opened.sum())
    return {"trades": trades, "symbols_traded": symbols}


def evaluate_strategy(
    strategy_id: str, returns: pd.Series, n_trials: int,
    dsr_threshold: float, min_obs: int,
    positions: pd.DataFrame | None = None, long_short: bool = False,
    notional: float = NOTIONAL_INR,
) -> GateResult:
    """Score a strategy's return series and apply the promotion gate.

    ``positions`` (optional) drives the plain-English trade counters; it never
    affects the pass/fail decision, which rests only on the return series."""
    rets = returns.dropna()
    n = int((rets != 0).sum())  # active observations
    stats = position_stats(positions) if positions is not None else {"trades": 0, "symbols_traded": 0}

    # Data gap vs. real result: no return series at all (or it never traded) is
    # a *missing input*, not a performance verdict (E7). news_sentiment /
    # nav_premium land here — they have no historical feed to replay over.
    if len(rets) < 2 or n == 0:
        return GateResult(
            strategy_id, n, 0.0, 0.0, 0.0, 0.0, None, False,
            reason="no data over this window (not judged)",
            trades=stats["trades"], symbols_traded=stats["symbols_traded"],
            long_short=long_short, data_gap=True,
        )
    if n < min_obs:
        return GateResult(
            strategy_id, n, 0.0, 0.0, 0.0, 0.0, None, False,
            reason=f"only {n} active obs (<{min_obs})",
            trades=stats["trades"], symbols_traded=stats["symbols_traded"],
            long_short=long_short,
        )

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
    active = rets[rets != 0]
    win_rate = float((active > 0).mean()) if len(active) else 0.0
    profit_inr = float(notional * res.total_return)
    return GateResult(
        strategy_id, n, round(sharpe, 3), round(res.total_return, 4),
        round(res.max_drawdown, 4), round(dsr, 3),
        round(mc_dd, 4) if mc_dd is not None else None, passes, reason,
        trades=stats["trades"], symbols_traded=stats["symbols_traded"],
        profit_inr=round(profit_inr, 2), win_rate=round(win_rate, 4),
        long_short=long_short,
    )


def run_gate(
    panel: dict[str, pd.DataFrame],
    per_symbol_strategies: list[Strategy],
    universe_strategies: list[UniverseStrategy],
    dsr_threshold: float = 0.90,
    min_obs: int = 30,
    fee_bps: float | None = None,   # None -> realistic Indian per-side costs
    step: int = 1,
    universe_step: int = 5,
    progress: Callable[[dict], None] | None = None,
    walk_forward: bool = False,
    wf_train: int = 252,
    wf_test: int = 63,
    n_trials: int | None = None,
) -> GateReport:
    """Backtest every strategy over ``panel`` and apply the promotion gate.

    ``progress`` (optional) is called with ``{"i", "total", "phase", "strategy",
    "result"?}`` before ("start") and after ("done") each strategy, so a caller
    can stream live progress instead of staring at a frozen terminal. A strategy
    declaring ``long_short = True`` is replayed with its short legs intact (E1).

    ``walk_forward`` (E2) additionally reports each strategy's held-out
    out-of-sample Sharpe (first ``wf_train`` bars as burn-in, scored on the
    stitched later ``wf_test`` windows) so an edge that decayed over time is
    visible even when its full-period Sharpe looks fine. It's a diagnostic — it
    never changes the pass/fail decision."""
    strategies: list = list(per_symbol_strategies) + list(universe_strategies)
    # DSR's multiple-testing penalty scales with n_trials. It defaults to the
    # number of strategies in THIS run, but can be pinned (e.g. to the 26-way
    # baseline) so a subset re-run stays comparable to the full-gate numbers.
    n_trials = n_trials if n_trials is not None else len(strategies)
    total = len(strategies)
    report = GateReport()
    # Representative series for the parameter-robustness probe (E2). Built once,
    # only when walk-forward hygiene is on (it's a diagnostic, not free).
    composite = composite_series(panel) if walk_forward else pd.Series(dtype=float)

    def _emit(phase: str, i: int, sid: str, result: GateResult | None = None) -> None:
        if progress is not None:
            try:
                progress({"i": i, "total": total, "phase": phase,
                          "strategy": sid, "result": result})
            except Exception:  # noqa: BLE001 - reporting must never break the run
                pass

    def _score(strat, positions, rets, long_short: bool) -> GateResult:
        result = evaluate_strategy(strat.id, rets, n_trials, dsr_threshold, min_obs,
                                   positions=positions, long_short=long_short)
        if walk_forward and not result.data_gap:
            result.oos_sharpe, result.oos_windows = walk_forward_oos(rets, wf_train, wf_test)
        if walk_forward and not composite.empty:
            result.plateau_ratio = plateau_probe(strat, composite)  # None if not tunable
        return result

    i = 0
    for strat in per_symbol_strategies:
        i += 1
        _emit("start", i, strat.id)
        long_short = bool(getattr(strat, "long_short", False))
        positions = replay_per_symbol(strat, panel, step=step, long_short=long_short)
        rets = portfolio_returns(positions, panel, fee_bps=fee_bps)
        result = _score(strat, positions, rets, long_short)
        report.results.append(result)
        _emit("done", i, strat.id, result)
    for strat in universe_strategies:
        i += 1
        _emit("start", i, strat.id)
        long_short = bool(getattr(strat, "long_short", False))
        symbols = strat.symbols() or list(panel.keys())
        sub_panel = {s: panel[s] for s in symbols if s in panel}
        positions = replay_universe(strat, sub_panel, step=universe_step, long_short=long_short)
        rets = portfolio_returns(positions, sub_panel, fee_bps=fee_bps)
        result = _score(strat, positions, rets, long_short)
        report.results.append(result)
        _emit("done", i, strat.id, result)
    return report
