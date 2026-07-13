"""Tests for the strategy-edge improvements: long-short replay (E1), honest
data-gap labeling (E7), and the human-readable trade/P&L stats."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.backtest import (
    NOTIONAL_INR,
    GateResult,
    composite_series,
    cross_sectional_dispersion,
    evaluate_strategy,
    format_inr,
    plateau_probe,
    portfolio_returns,
    position_stats,
    replay_universe,
    run_gate,
    walk_forward_oos,
)
from ats.services.strategies.base import Strategy, UniverseStrategy
from ats.services.strategies.library_trend_mr import ShortTermReversal


def _frame(close: np.ndarray) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2023-01-01", periods=len(close), name="date")
    return pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5,
         "close": close, "volume": np.full(len(close), 1e6)},
        index=idx,
    )


# --- format_inr (Indian grouping, ASCII-safe) -------------------------------
def test_format_inr_indian_grouping():
    assert format_inr(110000) == "Rs 1,10,000"
    assert format_inr(1234567) == "Rs 12,34,567"
    assert format_inr(-5000) == "Rs -5,000"
    assert format_inr(42) == "Rs 42"
    assert "₹" not in format_inr(100000)   # never the crash-prone ₹ glyph


# --- position stats ---------------------------------------------------------
def test_position_stats_counts_trades_and_symbols():
    pos = pd.DataFrame({
        "A": [0, 1, 1, 0, 1],      # two separate entries
        "B": [0, 0, -1, -1, 0],    # one short entry (counts)
        "C": [0, 0, 0, 0, 0],      # never traded
    }, dtype=float)
    s = position_stats(pos)
    assert s["symbols_traded"] == 2       # A and B, not C
    assert s["trades"] == 3               # A opened twice, B opened once
    assert position_stats(pd.DataFrame())["trades"] == 0


# --- E1: long-short replay keeps the short leg -------------------------------
class _FakePair(UniverseStrategy):
    """Always buy the (flat) cheap leg and short the (falling) rich leg."""

    id = "fake_pair"
    style = "stat_arb"
    min_bars = 5
    long_short = True

    def symbols(self) -> list[str]:
        return ["CHEAP", "RICH"]

    def evaluate_universe(self, history):
        return [
            SignalModel(strategy=self.id, symbol="CHEAP", stance=Stance.BUY,
                        conviction=1.0, features={}),
            SignalModel(strategy=self.id, symbol="RICH", stance=Stance.SELL,
                        conviction=1.0, features={}),
        ]


def test_long_short_replay_captures_the_short_leg():
    # CHEAP flat, RICH steadily falling: the edge lives entirely in the short.
    n = 60
    panel = {"CHEAP": _frame(np.full(n, 100.0)),
             "RICH": _frame(100.0 * (0.99 ** np.arange(n)))}
    strat = _FakePair()

    pos_ls = replay_universe(strat, panel, step=1, long_short=True)
    pos_lo = replay_universe(strat, panel, step=1, long_short=False)
    assert (pos_ls["RICH"] < 0).any()          # short position taken
    assert (pos_lo["RICH"] == 0).all()         # long-only flattens it away

    rets_ls = portfolio_returns(pos_ls, panel, fee_bps=0.0)
    rets_lo = portfolio_returns(pos_lo, panel, fee_bps=0.0)
    # Long-short harvests the falling rich leg; long-only sees ~nothing.
    assert rets_ls.sum() > 0.05
    assert abs(rets_lo.sum()) < 0.005


# --- E7: data gap is labeled, not scored as a failure -----------------------
def test_empty_returns_flagged_as_data_gap():
    r = evaluate_strategy("nav_premium", pd.Series(dtype=float), n_trials=5,
                          dsr_threshold=0.9, min_obs=30)
    assert r.data_gap is True and r.passes is False
    assert "no data" in r.reason
    assert "no data" in r.plain_english().lower()


def test_all_flat_returns_flagged_as_data_gap():
    flat = pd.Series(np.zeros(100))
    r = evaluate_strategy("news_sentiment", flat, n_trials=5,
                          dsr_threshold=0.9, min_obs=30)
    assert r.data_gap is True


# --- human-readable P&L on a real (winning) series --------------------------
def test_profit_and_win_rate_are_populated():
    rets = pd.Series(np.full(200, 0.001))     # steady small gains
    positions = pd.DataFrame({"X": np.ones(200)})
    r = evaluate_strategy("winner", rets, n_trials=1, dsr_threshold=0.9,
                          min_obs=30, positions=positions)
    assert r.profit_inr > 0                     # made money on the notional
    assert 0.0 <= r.win_rate <= 1.0 and r.win_rate > 0.9
    assert r.symbols_traded == 1
    assert format_inr(NOTIONAL_INR) == "Rs 1,00,000"


# --- realistic Indian costs (brokerage + taxes) -----------------------------
def test_cost_bps_asymmetry():
    from ats.services.execution.fees import cost_bps
    # STT (sell-side) makes selling far pricier than buying (stamp is buy-side).
    assert cost_bps("SELL") > cost_bps("BUY")
    assert 4.0 < cost_bps("BUY") < 8.0          # ~5.5 bps
    assert 12.0 < cost_bps("SELL") < 16.0       # ~14 bps


def test_engine_charges_asymmetric_buy_then_sell():
    from quant.backtest.engine import backtest_signals
    idx = pd.bdate_range("2023-01-01", periods=6)
    prices = pd.Series(100.0, index=idx)                 # flat price: gross = 0
    pos = pd.Series([0, 1, 1, 0, 0, 0], index=idx, dtype=float)  # one buy, one sell
    res = backtest_signals(prices, pos, buy_bps=10.0, sell_bps=20.0)
    # round trip pays buy + sell = 30 bps (tiny compounding aside).
    assert abs(res.total_return - (-0.003)) < 1e-4


def test_gate_default_costs_are_indian_and_penalize_churn():
    idx = pd.bdate_range("2023-01-01", periods=20)
    flat = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0,
                         "close": 100.0, "volume": 1e6}, index=idx)
    panel = {"X": flat}
    churn = pd.DataFrame({"X": [i % 2 for i in range(20)]}, index=idx, dtype=float)
    default_costs = portfolio_returns(churn, panel)              # Indian per-side
    zero_costs = portfolio_returns(churn, panel, fee_bps=0.0)    # frictionless
    assert abs(zero_costs.sum()) < 1e-9         # flat price, no fees -> ~0
    assert default_costs.sum() < 0              # churn on a flat market loses to costs


# --- E5: st_reversal trend filter (don't buy falling knives) -----------------
def _ohlc(closes) -> pd.DataFrame:
    idx = pd.bdate_range("2023-01-01", periods=len(closes), name="date")
    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": close, "high": close * 1.005, "low": close * 0.995,
                         "close": close, "volume": 1e6}, index=idx)


def _st_reversal_panel() -> dict:
    n = 80
    return {
        "AAA.NS": _ohlc(np.linspace(100, 60, n)),   # steady decline: strong downtrend + biggest loser
        "BBB.NS": _ohlc(np.full(n, 100.0)),         # flat
        "CCC.NS": _ohlc(np.linspace(100, 140, n)),  # steady rise: winner
        "DDD.NS": _ohlc(np.full(n, 100.0)),
        "EEE.NS": _ohlc(np.linspace(100, 120, n)),
    }


def test_st_reversal_skips_loser_in_strong_downtrend():
    st = ShortTermReversal(min_names=5)               # default adx_max=25 -> filter ON
    sigs = st.evaluate_universe(_st_reversal_panel())
    buys = [s.symbol for s in sigs if s.stance == Stance.BUY]
    assert "AAA.NS" not in buys                       # falling knife filtered out


def test_st_reversal_buys_the_loser_when_filter_disabled():
    st = ShortTermReversal(min_names=5, adx_max=0.0)  # filter OFF -> old behaviour
    sigs = st.evaluate_universe(_st_reversal_panel())
    buys = [s.symbol for s in sigs if s.stance == Stance.BUY]
    assert "AAA.NS" in buys                           # without the filter it catches the knife


# --- E2: parameter-robustness (plateau vs curve-fit spike) -------------------
class _AlwaysBuy(Strategy):
    id = "always_buy"
    style = "trend"
    min_bars = 5

    def evaluate(self, symbol, df):
        return SignalModel(strategy=self.id, symbol=symbol, stance=Stance.BUY,
                           conviction=1.0, features={})


class _CliffTunable(_AlwaysBuy):
    """Its 'edge' exists at exactly one parameter value — a curve-fit spike."""
    id = "cliff_param"

    def param_grid(self):
        return {"k": [1, 2, 3, 4, 5]}

    def signal_series(self, prices, k=3):
        pos = pd.Series(0.0, index=prices.index)
        if int(k) == 3:
            pos[:] = 1.0
        return pos


class _RobustTunable(_CliffTunable):
    """Its edge holds across a plateau of parameters (2, 3, 4)."""
    id = "robust_param"

    def signal_series(self, prices, k=3):
        pos = pd.Series(0.0, index=prices.index)
        if int(k) in (2, 3, 4):
            pos[:] = 1.0
        return pos


def _uptrend_panel(n_syms: int = 3, bars: int = 160) -> dict:
    up = 100.0 * (1.002 ** np.arange(bars))
    return {f"S{i}": _ohlc(up) for i in range(n_syms)}


def test_plateau_probe_on_real_tunable_strategy():
    from ats.services.strategies.library import SmaCrossover
    idx = pd.bdate_range("2022-01-01", periods=320)
    prices = pd.Series(100.0 * (1.001 ** np.arange(320)), index=idx)
    pr = plateau_probe(SmaCrossover(), prices)
    assert pr is not None and 0.0 <= pr <= 1.0


def test_plateau_probe_none_for_non_tunable():
    idx = pd.bdate_range("2022-01-01", periods=100)
    prices = pd.Series(100.0 + np.arange(100), index=idx)
    assert plateau_probe(_AlwaysBuy(), prices) is None       # no param_grid/signal_series


def test_gate_flags_curve_fit_parameters():
    panel = _uptrend_panel()
    assert not composite_series(panel).empty
    report = run_gate(panel, per_symbol_strategies=[_CliffTunable(), _RobustTunable()],
                      universe_strategies=[], dsr_threshold=0.5, min_obs=20, step=1,
                      walk_forward=True)
    by = {r.strategy: r for r in report.results}
    # The one-value spike is flagged; the plateau across {2,3,4} is not.
    assert by["cliff_param"].plateau_ratio is not None and by["cliff_param"].plateau_ratio < 0.6
    assert by["cliff_param"].is_curve_fit()
    assert by["robust_param"].plateau_ratio >= 0.6
    assert not by["robust_param"].is_curve_fit()
    assert "[curve-fit]" in report.summary()


# --- E3: broaden the universe (midcaps) for cross-sectional dispersion --------
def test_active_universe_midcap_flag_is_a_superset():
    from ats.services.reference import MIDCAP_UNIVERSE, UNIVERSE, active_universe
    base = active_universe(include_midcap=False)
    wide = active_universe(include_midcap=True)
    assert len(base) == len(UNIVERSE)
    assert len(wide) == len(UNIVERSE) + len(MIDCAP_UNIVERSE)
    assert {s for s, *_ in base}.issubset({s for s, *_ in wide})


def test_cross_sectional_dispersion_rises_with_diverse_names():
    same = 100.0 * (1.001 ** np.arange(120))
    lockstep = {"A": _ohlc(same), "B": _ohlc(same)}              # move identically -> ~0
    diverse = dict(
        lockstep,
        C=_ohlc(100.0 * (0.999 ** np.arange(120))),             # opposing trend
        D=_ohlc(100.0 + 5.0 * np.sin(np.arange(120) / 3.0)),    # choppy
    )
    assert cross_sectional_dispersion(lockstep) < cross_sectional_dispersion(diverse)


# --- E2: walk-forward out-of-sample ----------------------------------------
def test_walk_forward_oos_needs_a_full_window():
    short = pd.Series(np.full(100, 0.001))
    assert walk_forward_oos(short, train=252, test=63) == (0.0, 0)


def test_walk_forward_oos_scores_the_held_out_tail():
    rets = pd.Series(np.full(400, 0.001),
                     index=pd.bdate_range("2022-01-01", periods=400))
    oos, n = walk_forward_oos(rets, train=252, test=63)
    assert n >= 1 and oos > 0        # steady gains persist out-of-sample


def _result(sharpe, oos):
    return GateResult("x", 300, sharpe, 0.1, -0.1, 0.5, -0.1, False, oos_sharpe=oos)


def test_oos_decayed_flag():
    assert _result(2.0, 0.5).oos_decayed() is True    # later Sharpe < half of full
    assert _result(2.0, 1.8).oos_decayed() is False   # edge holds up
    assert _result(2.0, None).oos_decayed() is False  # walk-forward didn't run
    assert _result(-0.5, -2.0).oos_decayed() is False # already-losing: not "decay"


class _Long(Strategy):
    id = "long_test"
    style = "trend"
    min_bars = 5

    def evaluate(self, symbol, df):
        return SignalModel(strategy=self.id, symbol=symbol, stance=Stance.BUY,
                           conviction=1.0, features={})


def test_run_gate_walk_forward_populates_oos():
    idx = pd.bdate_range("2021-01-01", periods=400, name="date")
    close = 100.0 * (1.001 ** np.arange(400))
    panel = {"S": pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5,
         "close": close, "volume": np.full(400, 1e6)}, index=idx)}
    report = run_gate(panel, per_symbol_strategies=[_Long()], universe_strategies=[],
                      dsr_threshold=0.5, min_obs=20, step=1, walk_forward=True)
    r = report.results[0]
    assert r.oos_sharpe is not None and r.oos_windows >= 1
    # And a plain run leaves it untouched (diagnostic is opt-in).
    plain = run_gate(panel, per_symbol_strategies=[_Long()], universe_strategies=[],
                     dsr_threshold=0.5, min_obs=20, step=1)
    assert plain.results[0].oos_sharpe is None
