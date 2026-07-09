"""Tests for the strategy auto-trader (signal consensus -> proposal).

These exercise the new bridge that lets the quant strategies place paper orders
on their own: a consensus of paper-status strategy signals becomes a PROPOSAL
that flows through the normal Risk -> Execution path. Pure logic, no DB.
"""

from __future__ import annotations

import asyncio

from ats.core.events import Topic
from ats.services.execution.strategy_trader import StrategyTraderService


class _FakeBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


class _FakeExec:
    def __init__(self, positions: list[dict] | None = None) -> None:
        self._positions = positions or []

    def get_snapshot(self) -> dict:
        return {"equity": 100_000.0, "positions": self._positions, "holdings_value": 0.0}


def _trader(positions: list[dict] | None = None) -> tuple[StrategyTraderService, _FakeBus]:
    bus = _FakeBus()
    t = StrategyTraderService()
    t._bus = bus
    t._execution = _FakeExec(positions)
    return t, bus


def _sig(strategy: str, symbol: str, stance: str, conviction: float) -> dict:
    return {"strategy": strategy, "symbol": symbol, "stance": stance, "conviction": conviction}


def test_bullish_signal_proposes_buy():
    t, bus = _trader()
    res = asyncio.run(t.handle_signal(_sig("sma_crossover", "TCS.NS", "buy", 0.6)))
    assert res["status"] == "proposed"
    assert res["action"] == "BUY"
    assert len(bus.published) == 1
    topic, payload = bus.published[0]
    assert topic == Topic.PROPOSAL
    assert payload["action"] == "BUY"
    assert payload["symbol"] == "TCS.NS"
    assert payload["contributors"]["source"] == "strategy_consensus"
    # target weight is the per-name cap; Risk does the actual sizing/guardrails.
    assert payload["target_weight"] > 0


def test_weak_signal_below_threshold_does_not_trade():
    t, bus = _trader()
    res = asyncio.run(t.handle_signal(_sig("sma_crossover", "TCS.NS", "buy", 0.05)))
    assert res["status"] == "no_action"
    assert bus.published == []


def test_consensus_netting_bull_minus_bear():
    t, _ = _trader()
    t._views["TCS.NS"] = {
        "sma_crossover": (1, 0.6),       # bullish
        "mean_reversion": (-1, 0.4),     # bearish
    }
    net, bull_agree, voters = t._net_score("TCS.NS")
    assert voters == 2
    assert bull_agree == 1
    assert abs(net - (0.6 - 0.4) / 2) < 1e-9  # = 0.1


def test_holding_and_bearish_consensus_exits():
    t, bus = _trader(positions=[{"symbol": "TCS.NS", "qty": 10, "market_value": 30000.0}])
    res = asyncio.run(t.handle_signal(_sig("donchian_trend", "TCS.NS", "strong_sell", 0.8)))
    assert res["status"] == "proposed"
    assert res["action"] == "SELL"
    _, payload = bus.published[0]
    assert payload["action"] == "SELL"
    assert payload["target_weight"] == 0.0  # flatten the name


def test_index_symbols_never_proposed():
    t, bus = _trader()
    res = asyncio.run(t.handle_signal(_sig("ts_momentum", "^NSEI", "buy", 0.9)))
    assert res["status"] == "not_tradeable"
    assert bus.published == []


def test_per_symbol_cooldown_blocks_churn():
    t, bus = _trader()
    first = asyncio.run(t.handle_signal(_sig("sma_crossover", "INFY.NS", "buy", 0.7)))
    assert first["status"] == "proposed"
    # Immediate second actionable signal on the same name is debounced.
    second = asyncio.run(t.handle_signal(_sig("donchian_trend", "INFY.NS", "buy", 0.7)))
    assert second["status"] == "cooldown"
    assert len(bus.published) == 1


def test_not_holding_and_bearish_is_noop():
    # A bearish signal on a name we don't own should not short (long-only).
    t, bus = _trader()
    res = asyncio.run(t.handle_signal(_sig("mean_reversion", "WIPRO.NS", "sell", 0.7)))
    assert res["status"] == "no_action"
    assert bus.published == []
