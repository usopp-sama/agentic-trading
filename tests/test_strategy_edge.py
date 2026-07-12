"""Tests for the strategy-edge improvements: long-short replay (E1), honest
data-gap labeling (E7), and the human-readable trade/P&L stats."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import SignalModel, Stance
from ats.services.strategies.backtest import (
    NOTIONAL_INR,
    evaluate_strategy,
    format_inr,
    portfolio_returns,
    position_stats,
    replay_universe,
)
from ats.services.strategies.base import UniverseStrategy


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
