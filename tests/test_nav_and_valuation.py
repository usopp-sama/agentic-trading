"""Tests for the NAV-premium sleeve, tradeability veto, and the
fundamentals-based valuation signal."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ats.core.schemas import Stance
from ats.services.agents.context import ContextAssembler
from ats.services.agents.tools import Providers
from ats.services.risk.guardrails import is_tradeable
from ats.services.strategies.library import NavPremium
from quant.data.fetch import synthetic_prices


def _frame(close: np.ndarray) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2024-01-01", periods=len(close), name="date")
    return pd.DataFrame(
        {
            "open": close, "high": close + 0.5, "low": close - 0.5,
            "close": close, "volume": np.full(len(close), 1e6),
        },
        index=idx,
    )


def _etf_universe(final_premium: float) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(31)
    underlying = 30.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, 120)))
    etf = underlying * 3.1  # stable fair ratio
    etf[-1] *= 1.0 + final_premium  # push the last print off fair value
    return {"ETF.NS": _frame(etf), "UND=F": _frame(underlying)}


# --- NAV premium sleeve ---------------------------------------------------------
def test_nav_buys_discount_and_only_signals_etf():
    strat = NavPremium(etf_underlyings=[("ETF.NS", "UND=F")])
    signals = strat.evaluate_universe(_etf_universe(-0.03))  # 3% discount
    assert [s.symbol for s in signals] == ["ETF.NS"]  # never the underlying
    sig = signals[0]
    assert sig.stance == Stance.BUY
    assert sig.features["premium_pct"] < -1.5
    assert sig.features["underlying"] == "UND=F"


def test_nav_sells_premium():
    strat = NavPremium(etf_underlyings=[("ETF.NS", "UND=F")])
    (sig,) = strat.evaluate_universe(_etf_universe(0.03))
    assert sig.stance == Stance.SELL


def test_nav_neutral_near_fair_value():
    strat = NavPremium(etf_underlyings=[("ETF.NS", "UND=F")])
    (sig,) = strat.evaluate_universe(_etf_universe(0.0))
    assert sig.stance == Stance.NEUTRAL


def test_nav_skips_missing_underlying():
    strat = NavPremium(etf_underlyings=[("ETF.NS", "MISSING")])
    history = {"ETF.NS": _frame(100.0 + np.arange(120.0))}
    assert strat.evaluate_universe(history) == []


def test_nav_declares_needed_symbols():
    strat = NavPremium()
    assert "SILVERBEES.NS" in strat.symbols()
    assert "SI=F" in strat.symbols()


# --- tradeability veto -------------------------------------------------------------
def test_only_equities_and_etfs_are_tradeable():
    assert is_tradeable("EQ")
    assert is_tradeable("ETF")
    assert is_tradeable(None)  # unknown defaults to EQ
    assert not is_tradeable("INDEX")
    assert not is_tradeable("COMMODITY")


# --- fundamentals-based valuation signal -----------------------------------------------
class _FakeMd:
    def __init__(self) -> None:
        self._df = synthetic_prices(n=120, seed=9)

    def get_history(self, symbol, limit: int = 250):
        return self._df

    def latest_price(self, symbol):
        return float(self._df["close"].iloc[-1])


class _FakeFundamentals:
    def __init__(self, table: dict) -> None:
        self._table = table

    def all_latest(self) -> dict:
        return self._table

    def get(self, symbol):
        return self._table.get(symbol)


def _universe_with(symbol_pe_pb: tuple[float, float]) -> dict:
    # Six peers at median-ish multiples plus the symbol under test.
    table = {
        f"PEER{i}.NS": {"pe": 20.0 + i, "pb": 3.0 + 0.1 * i} for i in range(6)
    }
    table["X.NS"] = {"pe": symbol_pe_pb[0], "pb": symbol_pe_pb[1]}
    return table


def _valuation_for(pe: float, pb: float) -> float:
    providers = Providers(
        market_data=_FakeMd(),
        fundamentals=_FakeFundamentals(_universe_with((pe, pb))),
    )
    ctx = ContextAssembler(providers).assemble(
        {"id": "valuer", "inputs": ["valuation"]}, "X.NS"
    )
    return ctx["signals"]["valuation"]


def test_cheap_stock_scores_positive():
    assert _valuation_for(pe=8.0, pb=1.0) > 0.3


def test_expensive_stock_scores_negative():
    assert _valuation_for(pe=60.0, pb=9.0) < -0.3


def test_loss_maker_falls_back_to_price_proxy():
    # Negative P/E must not read as "cheap"; with no usable ratios the
    # signal falls back to the price-vs-60-day-mean proxy (still emitted).
    val = _valuation_for(pe=-5.0, pb=-1.0)
    assert -1.0 <= val <= 1.0


def test_no_fundamentals_service_still_emits_signal():
    providers = Providers(market_data=_FakeMd())
    ctx = ContextAssembler(providers).assemble(
        {"id": "valuer", "inputs": ["valuation"]}, "X.NS"
    )
    assert "valuation" in ctx["signals"]
