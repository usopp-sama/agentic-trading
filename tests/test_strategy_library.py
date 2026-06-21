"""Tests for the proven-strategy library (roadmap Part 7).

Each strategy is exercised on engineered price paths where the correct
answer is unambiguous, plus guard tests for the filters that protect
capital (trend filter, skip window, long-only pair legs).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import Stance
from ats.services.strategies.library import (
    DonchianTrend,
    FactorComposite,
    PairsZScore,
    Rsi2MeanReversion,
    TimeSeriesMomentum,
)


def _frame(close: np.ndarray, spread: float = 0.5) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2024-01-01", periods=len(close), name="date")
    return pd.DataFrame(
        {
            "open": np.concatenate([[close[0]], close[:-1]]),
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "volume": np.full(len(close), 1_000_000.0),
        },
        index=idx,
    )


# --- Donchian trend following ------------------------------------------------
def test_donchian_buys_breakout():
    # Strictly rising: every close is a breakout of the prior 55-bar high.
    df = _frame(100.0 + np.arange(80) * 2.0)
    sig = DonchianTrend().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.conviction > 0


def test_donchian_sells_breakdown():
    df = _frame(300.0 - np.arange(80) * 2.0)
    sig = DonchianTrend().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.SELL


def test_donchian_neutral_inside_channel():
    rng = np.random.default_rng(11)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.05, size=80))
    df = _frame(close, spread=8.0)  # wide bars -> wide channel -> no breakout
    sig = DonchianTrend().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.NEUTRAL


# --- RSI(2) pullback ----------------------------------------------------------
def test_rsi2_buys_pullback_in_uptrend():
    # Long steady uptrend, then two sharp down days: oversold but still
    # comfortably above the 200-SMA.
    close = list(100.0 * (1.002 ** np.arange(248)))
    close += [close[-1] * 0.97, close[-1] * 0.94]
    sig = Rsi2MeanReversion().evaluate("X", _frame(np.array(close)))
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.features["trend_ok"] is True
    assert sig.conviction >= 0.5


def test_rsi2_stands_aside_below_trend():
    # Oversold in a downtrend must NOT buy (the falling-knife filter).
    close = 400.0 * (0.998 ** np.arange(248))
    close = np.concatenate([close, [close[-1] * 0.97, close[-1] * 0.94]])
    sig = Rsi2MeanReversion().evaluate("X", _frame(close))
    assert sig is not None and sig.stance == Stance.NEUTRAL
    assert sig.features["trend_ok"] is False


def test_rsi2_exits_overbought():
    close = list(100.0 * (1.002 ** np.arange(248)))
    close += [close[-1] * 1.03, close[-1] * 1.06]  # two strong up days
    sig = Rsi2MeanReversion().evaluate("X", _frame(np.array(close)))
    assert sig is not None and sig.stance == Stance.SELL


# --- 12-1 time-series momentum -------------------------------------------------
def test_momentum_buys_uptrend_despite_recent_dip():
    # Strong year-long climb, then a sharp final month. The skip window
    # must ignore the recent crash and still read positive momentum.
    climb = 100.0 * (1.001 ** np.arange(280))
    dip = climb[-1] * (0.99 ** np.arange(1, 21))
    sig = TimeSeriesMomentum().evaluate("X", _frame(np.concatenate([climb, dip])))
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.features["mom_return"] > 0


def test_momentum_sells_downtrend():
    decline = 400.0 * (0.999 ** np.arange(300))
    sig = TimeSeriesMomentum().evaluate("X", _frame(decline))
    assert sig is not None and sig.stance == Stance.SELL


def test_momentum_neutral_when_flat():
    rng = np.random.default_rng(13)
    flat = 100.0 + np.cumsum(rng.normal(0.0, 0.02, size=300))
    sig = TimeSeriesMomentum().evaluate("X", _frame(flat))
    assert sig is not None and sig.stance == Stance.NEUTRAL


def test_momentum_requires_enough_history():
    short = _frame(100.0 + np.arange(100, dtype=float))
    assert TimeSeriesMomentum().evaluate("X", short) is None


# --- Pairs z-score --------------------------------------------------------------
def _pair_history(diverge: float) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(17)
    base = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, size=120)))
    a = base * 1.5
    b = base.copy()
    # Push A rich vs B over the last bars.
    a[-3:] = a[-3:] * (1.0 + diverge)
    return {"A": _frame(a), "B": _frame(b)}


def test_pairs_buys_cheap_leg_when_spread_stretches():
    strat = PairsZScore(pairs=[("A", "B")])
    signals = {s.symbol: s for s in strat.evaluate_universe(_pair_history(0.10))}
    assert signals["B"].stance == Stance.BUY      # cheap leg
    assert signals["A"].stance == Stance.SELL     # rich leg (flatten only)
    assert signals["A"].features["zscore"] >= 2.0


def test_pairs_neutral_when_converged():
    strat = PairsZScore(pairs=[("A", "B")])
    signals = strat.evaluate_universe(_pair_history(0.0))
    assert all(s.stance == Stance.NEUTRAL for s in signals)


def test_pairs_skips_missing_leg():
    strat = PairsZScore(pairs=[("A", "MISSING")])
    history = {"A": _frame(100.0 + np.arange(120, dtype=float))}
    assert strat.evaluate_universe(history) == []


def test_pairs_declares_needed_symbols():
    strat = PairsZScore(pairs=[("A", "B"), ("B", "C")])
    assert strat.symbols() == ["A", "B", "C"]


# --- factor composite ------------------------------------------------------------
def _factor_universe() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(23)
    n = 300
    # WINNER: strong steady climb (high momentum, low vol).
    winner = 100.0 * (1.002 ** np.arange(n))
    # CHOPPY: same total climb but violently volatile.
    choppy = 100.0 * (1.002 ** np.arange(n)) * np.exp(
        np.cumsum(rng.normal(0.0, 0.04, n)) - np.cumsum(rng.normal(0.0, 0.04, n)).mean()
    )
    # LAGGARD: flat.
    laggard = np.full(n, 100.0) + rng.normal(0.0, 0.2, n)
    return {
        "WIN": _frame(winner),
        "CHOP": _frame(np.abs(choppy) + 1.0),
        "LAG": _frame(laggard),
        "^NSEI": _frame(winner),          # index must be ignored
        "SILVERBEES.NS": _frame(winner),  # ETF must be ignored
    }


def test_factor_picks_steady_winner_and_excludes_non_equity():
    strat = FactorComposite(top_n=1)
    signals = strat.evaluate_universe(_factor_universe())
    buys = [s for s in signals if s.stance == Stance.BUY]
    assert [s.symbol for s in buys] == ["WIN"]
    assert all(s.symbol not in {"^NSEI", "SILVERBEES.NS"} for s in signals)


def test_factor_holds_between_rebalances():
    strat = FactorComposite(top_n=1, rebalance_calendar_days=90)
    universe = _factor_universe()
    assert strat.evaluate_universe(universe) != []
    # Same day again: inside the rebalance window -> no churn.
    assert strat.evaluate_universe(universe) == []


def test_factor_flattens_dropped_names():
    strat = FactorComposite(top_n=1, rebalance_calendar_days=0)
    universe = _factor_universe()
    strat.evaluate_universe(universe)  # basket = {WIN}
    # Crash the winner violently (noisy, so its vol rank tanks too);
    # the steady laggard becomes the relative winner.
    rng = np.random.default_rng(99)
    crashed = universe["WIN"]["close"].to_numpy().copy()
    crashed[-100:] = (
        crashed[-100]
        * (0.97 ** np.arange(100))
        * np.exp(rng.normal(0.0, 0.03, 100))
    )
    universe["WIN"] = _frame(crashed)
    signals = {s.symbol: s for s in strat.evaluate_universe(universe)}
    assert signals["WIN"].stance == Stance.NEUTRAL  # flattened on drop


def test_factor_skips_short_history():
    short = {"X": _frame(100.0 + np.arange(50, dtype=float))}
    assert FactorComposite().evaluate_universe(short) == []


def test_factor_value_quality_lift_cheap_quality_name():
    # Two price-identical names: with price factors alone they tie, so
    # fundamentals must decide. CHEAPQ is cheap (low PE/PB) and high
    # quality (high ROE, low debt); RICHJ is the opposite.
    n = 300
    closes = 100.0 * (1.001 ** np.arange(n))
    universe = {"CHEAPQ": _frame(closes), "RICHJ": _frame(closes.copy())}
    fund = {
        "CHEAPQ": {"pe": 10.0, "pb": 1.2, "roe": 0.28, "debt_to_equity": 0.1},
        "RICHJ": {"pe": 55.0, "pb": 9.0, "roe": 0.06, "debt_to_equity": 2.0},
    }
    strat = FactorComposite(top_n=1, rebalance_calendar_days=0)
    strat.set_fundamentals(lambda: fund)
    signals = {s.symbol: s for s in strat.evaluate_universe(universe)}
    assert signals["CHEAPQ"].stance == Stance.BUY
    assert "RICHJ" not in signals or signals["RICHJ"].stance != Stance.BUY
    assert signals["CHEAPQ"].features["value"] > 0.5
    assert signals["CHEAPQ"].features["quality"] > 0.5


def test_factor_survives_broken_fundamentals_provider():
    strat = FactorComposite(top_n=1)
    strat.set_fundamentals(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    signals = strat.evaluate_universe(_factor_universe())
    # Falls back to price-only factors instead of dying.
    assert any(s.stance == Stance.BUY for s in signals)


def test_factor_ignores_negative_pe():
    n = 300
    closes = 100.0 * (1.001 ** np.arange(n))
    universe = {"LOSSCO": _frame(closes), "PROFITCO": _frame(closes.copy())}
    fund = {
        "LOSSCO": {"pe": -8.0, "pb": 1.0, "roe": -0.05, "debt_to_equity": 0.5},
        "PROFITCO": {"pe": 20.0, "pb": 3.0, "roe": 0.15, "debt_to_equity": 0.5},
    }
    strat = FactorComposite(top_n=2, rebalance_calendar_days=0)
    strat.set_fundamentals(lambda: fund)
    signals = {s.symbol: s for s in strat.evaluate_universe(universe)}
    # LOSSCO's negative PE is excluded from the value rank, not ranked "cheapest".
    assert "value" not in signals["LOSSCO"].features or signals["LOSSCO"].features["value"] <= 1.0
    assert signals["PROFITCO"].stance == Stance.BUY


# === Phase-2 strategy-library expansion ======================================
from ats.services.strategies.library_trend_mr import (  # noqa: E402
    CrossSectionalMomentum,
    DualMomentum,
    FiftyTwoWeekHigh,
    MacdAdxTrend,
    OuKeltnerReversion,
    ShortTermReversal,
)
from ats.services.strategies.library_factors import (  # noqa: E402
    CointegrationPairs,
    LowVolBAB,
    QualityFactor,
    SizeFactor,
    ValueFactor,
)
from ats.services.strategies.library_events import (  # noqa: E402
    NewsSentimentMomentum,
    PostEarningsDrift,
    TurnOfMonth,
    VolatilityTarget,
)


def _xs_universe() -> dict[str, pd.DataFrame]:
    """Five equities with monotonically decreasing momentum + an index."""
    n = 300
    uni = {}
    for i, sym in enumerate(["A.NS", "B.NS", "C.NS", "D.NS", "E.NS"]):
        # A strongest uptrend, E falling.
        drift = 0.003 - i * 0.0015
        uni[sym] = _frame(100.0 * np.cumprod(1.0 + np.full(n, drift)))
    uni["^NSEI"] = _frame(100.0 * (1.0005 ** np.arange(n)))
    return uni


# --- Trend / momentum --------------------------------------------------------
def test_fifty_two_week_high_buys_near_high_in_uptrend():
    df = _frame(100.0 * (1.001 ** np.arange(300)))
    sig = FiftyTwoWeekHigh().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.features["nearness"] >= 0.95


def test_fifty_two_week_high_sells_far_below_high_downtrend():
    # Rise then a deep, sustained fall well below the trailing high.
    up = 100.0 * (1.002 ** np.arange(150))
    down = up[-1] * (0.99 ** np.arange(150))
    sig = FiftyTwoWeekHigh().evaluate("X", _frame(np.concatenate([up, down])))
    assert sig is not None and sig.stance == Stance.SELL


def test_macd_adx_neutral_in_chop():
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0.0, 0.1, size=120))
    sig = MacdAdxTrend().evaluate("X", _frame(close))
    # Low ADX -> the filter forces NEUTRAL regardless of MACD wiggle.
    assert sig is not None and sig.stance == Stance.NEUTRAL


def test_macd_adx_buys_strong_uptrend():
    sig = MacdAdxTrend().evaluate("X", _frame(100.0 + 1.5 * np.arange(120)))
    assert sig is not None and sig.stance == Stance.BUY
    assert sig.features["adx"] >= 20.0


def test_cross_sectional_momentum_longs_winner_flattens_loser():
    strat = CrossSectionalMomentum(min_names=3)
    signals = {s.symbol: s for s in strat.evaluate_universe(_xs_universe())}
    assert signals["A.NS"].stance == Stance.BUY
    assert signals["E.NS"].stance == Stance.SELL
    # Index is never ranked by an equity model.
    assert "^NSEI" not in signals


def test_cross_sectional_momentum_respects_rebalance_cadence():
    strat = CrossSectionalMomentum(min_names=3, rebalance_days=21)
    uni = _xs_universe()
    assert strat.evaluate_universe(uni)  # first pass rebalances
    assert strat.evaluate_universe(uni) == []  # same day -> no churn


def test_dual_momentum_goes_to_cash_when_all_negative():
    n = 300
    uni = {s: _frame(400.0 * (0.999 ** np.arange(n)))
           for s in ["A.NS", "B.NS", "C.NS"]}
    strat = DualMomentum(top_n=2, abs_floor=0.0)
    signals = strat.evaluate_universe(uni)
    # Absolute filter: nothing has positive trailing return -> no BUYs.
    assert all(s.stance != Stance.BUY for s in signals)


def test_short_term_reversal_buys_recent_loser():
    n = 60
    uni = {}
    # WIN spiked up last week, LOSE dropped last week.
    base = 100.0 * np.ones(n)
    win = base.copy(); win[-5:] = [102, 104, 106, 108, 110]
    lose = base.copy(); lose[-5:] = [98, 96, 94, 92, 90]
    uni["WIN"] = _frame(win)
    uni["LOSE"] = _frame(lose)
    uni["MID1"] = _frame(base.copy())
    uni["MID2"] = _frame(base.copy())
    uni["MID3"] = _frame(base.copy())
    signals = {s.symbol: s for s in ShortTermReversal(min_names=3).evaluate_universe(uni)}
    assert signals["LOSE"].stance == Stance.BUY
    assert signals["WIN"].stance == Stance.SELL


def test_ou_keltner_buys_dip_sells_spike():
    rng = np.random.default_rng(3)
    rng_series = 100.0 + 2.0 * np.sin(np.arange(80) / 3.0)
    dip = np.concatenate([rng_series, [97.0, 95.0, 94.0]])
    spike = np.concatenate([rng_series, [103.0, 105.0, 106.0]])
    assert OuKeltnerReversion().evaluate("X", _frame(dip)).stance == Stance.BUY
    assert OuKeltnerReversion().evaluate("X", _frame(spike)).stance == Stance.SELL


def test_ou_keltner_stands_aside_in_strong_trend():
    sig = OuKeltnerReversion(adx_max=15.0).evaluate(
        "X", _frame(100.0 + 2.0 * np.arange(120))
    )
    assert sig is not None and sig.stance == Stance.NEUTRAL


# --- Factor sleeves ----------------------------------------------------------
def _factor_fundamentals() -> dict:
    return {
        "A.NS": {"pe": 10, "pb": 1.0, "roe": 0.25, "profit_margin": 0.2,
                 "debt_to_equity": 0.2, "market_cap": 5e10},
        "B.NS": {"pe": 15, "pb": 2.0, "roe": 0.18, "profit_margin": 0.15,
                 "debt_to_equity": 0.5, "market_cap": 2e11},
        "C.NS": {"pe": 25, "pb": 3.0, "roe": 0.12, "profit_margin": 0.10,
                 "debt_to_equity": 0.8, "market_cap": 8e11},
        "D.NS": {"pe": 40, "pb": 5.0, "roe": 0.08, "profit_margin": 0.05,
                 "debt_to_equity": 1.5, "market_cap": 2e12},
    }


def test_value_factor_prefers_cheap_names():
    strat = ValueFactor(top_n=2, rebalance_calendar_days=0)
    strat.set_fundamentals(_factor_fundamentals)
    signals = {s.symbol: s for s in strat.evaluate_universe(_xs_universe())}
    # Cheapest (A) ranks top; expensive (D) is not bought.
    assert signals["A.NS"].stance == Stance.BUY
    assert "D.NS" not in signals or signals["D.NS"].stance != Stance.BUY


def test_quality_factor_prefers_high_roe_low_debt():
    strat = QualityFactor(top_n=1, rebalance_calendar_days=0)
    strat.set_fundamentals(_factor_fundamentals)
    signals = {s.symbol: s for s in strat.evaluate_universe(_xs_universe())}
    assert signals["A.NS"].stance == Stance.BUY


def test_size_factor_prefers_small_cap():
    # Universe restricted to names that all carry a market cap, so the
    # dollar-volume fallback never decides the ranking.
    n = 300
    uni = {s: _frame(100.0 * (1.001 ** np.arange(n))) for s in ["A.NS", "B.NS", "C.NS", "D.NS"]}
    strat = SizeFactor(top_n=1, rebalance_calendar_days=0)
    strat.set_fundamentals(_factor_fundamentals)
    signals = {s.symbol: s for s in strat.evaluate_universe(uni)}
    assert signals["A.NS"].stance == Stance.BUY  # smallest market cap


def test_low_vol_bab_prefers_calm_names():
    n = 200
    rng = np.random.default_rng(9)
    uni = {
        "CALM.NS": _frame(100.0 * np.cumprod(1.0 + 0.0005 + 0.003 * rng.standard_normal(n))),
        "WILD.NS": _frame(100.0 * np.cumprod(1.0 + 0.0005 + 0.04 * rng.standard_normal(n))),
        "^NSEI": _frame(100.0 * np.cumprod(1.0 + 0.0004 + 0.008 * rng.standard_normal(n))),
    }
    strat = LowVolBAB(top_n=1, rebalance_calendar_days=0, vol_window=120, beta_window=120)
    signals = {s.symbol: s for s in strat.evaluate_universe(uni)}
    assert signals["CALM.NS"].stance == Stance.BUY


def test_low_vol_bab_survives_broken_fundamentals():
    # Price-only sleeve must not need fundamentals at all.
    strat = LowVolBAB(top_n=1, rebalance_calendar_days=0, vol_window=120, beta_window=120)
    n = 200
    rng = np.random.default_rng(2)
    uni = {"X.NS": _frame(100.0 * np.cumprod(1.0 + 0.003 * rng.standard_normal(n))),
           "^NSEI": _frame(100.0 * np.cumprod(1.0 + 0.008 * rng.standard_normal(n)))}
    assert any(s.stance == Stance.BUY for s in strat.evaluate_universe(uni))


def test_cointegration_pairs_trades_stretched_stationary_spread():
    rng = np.random.default_rng(2)
    logx = np.cumsum(0.001 + 0.02 * rng.standard_normal(300)) + 5.3
    noise = np.zeros(300)
    for i in range(1, 300):
        noise[i] = 0.7 * noise[i - 1] + 0.01 * rng.standard_normal()
    x = np.exp(logx)
    y = np.exp(1.0 * logx + 0.05 + noise)
    y[-1] *= 1.08  # stretch the current spread to trigger entry
    strat = CointegrationPairs(
        candidates=[("PX.NS", "PY.NS")], formation=250, z_window=40, entry_z=2.0
    )
    signals = {s.symbol: s.stance for s in strat.evaluate_universe(
        {"PX.NS": _frame(y), "PY.NS": _frame(x)})}
    assert strat._active  # the pair passed cointegration
    assert Stance.BUY in signals.values() and Stance.SELL in signals.values()


def test_cointegration_rejects_independent_random_walks():
    rng = np.random.default_rng(5)
    x = np.exp(np.cumsum(0.02 * rng.standard_normal(300)) + 5.0)
    y = np.exp(np.cumsum(0.02 * rng.standard_normal(300)) + 5.0)
    strat = CointegrationPairs(candidates=[("PX.NS", "PY.NS")], formation=250)
    strat.evaluate_universe({"PX.NS": _frame(y), "PY.NS": _frame(x)})
    assert not strat._active  # not cointegrated -> no active pair


# --- Event / sentiment / seasonal / vol --------------------------------------
def test_pead_rides_positive_earnings_gap():
    rng = np.random.default_rng(3)
    base = 100.0 * np.cumprod(1.0 + 0.0002 + 0.01 * rng.standard_normal(120))
    base[-3] *= 1.12  # earnings-day gap up
    vol = np.full(120, 1e6)
    vol[-3] = 3e6
    df = _frame(base)
    df["volume"] = vol
    sig = PostEarningsDrift().evaluate("X", df)
    assert sig is not None and sig.stance == Stance.BUY


def test_news_sentiment_requires_min_article_count():
    df = _frame(100.0 * np.cumprod(1.0 + np.full(60, 0.002)))
    strat = NewsSentimentMomentum()
    strat.set_sentiment(lambda sym, hours: {"mean_score": 0.6, "count": 1})
    assert strat.evaluate("X", df).stance == Stance.NEUTRAL
    strat.set_sentiment(lambda sym, hours: {"mean_score": 0.6, "count": 5})
    assert strat.evaluate("X", df).stance == Stance.BUY


def test_news_sentiment_inert_without_provider():
    df = _frame(100.0 * np.cumprod(1.0 + np.full(60, 0.002)))
    assert NewsSentimentMomentum().evaluate("X", df) is None


def test_turn_of_month_window():
    on_first = pd.DataFrame(
        {"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1e6},
        index=pd.to_datetime(["2024-01-30", "2024-01-31", "2024-02-01"]),
    )
    mid = pd.DataFrame(
        {"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1e6},
        index=pd.to_datetime(["2024-02-13", "2024-02-14", "2024-02-15"]),
    )
    assert TurnOfMonth().evaluate("X", on_first).stance == Stance.BUY
    assert TurnOfMonth().evaluate("X", mid).stance == Stance.NEUTRAL


def test_volatility_target_derisks_in_high_vol():
    rng = np.random.default_rng(4)
    calm = 100.0 * np.cumprod(1.0 + 0.001 + 0.004 * rng.standard_normal(120))
    wild = 100.0 * np.cumprod(1.0 + 0.001 + 0.05 * rng.standard_normal(120))
    calm_sig = VolatilityTarget().evaluate("X", _frame(calm))
    wild_sig = VolatilityTarget().evaluate("X", _frame(wild))
    assert calm_sig.stance == Stance.BUY and calm_sig.conviction > 0
    assert wild_sig.stance == Stance.NEUTRAL  # vol blew past max_vol


def test_factories_match_reference_registry():
    from ats.services.reference import STRATEGIES
    from ats.services.strategies.library import (
        default_strategies,
        default_universe_strategies,
    )

    registry = {row[0] for row in STRATEGIES}
    instantiated = (
        {s.id for s in default_strategies()}
        | {s.id for s in default_universe_strategies()}
        | {"vol_premium"}  # the options sleeve runs in its own service
    )
    assert registry == instantiated
