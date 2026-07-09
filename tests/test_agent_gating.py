"""Tests for the autonomous-evaluation cost gating helpers."""

from __future__ import annotations

from ats.services.agents.gating import SymbolCooldown, rank_symbols


def test_rank_symbols_drops_indices_and_caps():
    out = rank_symbols(
        ["^NSEI", "TCS", "INFY", "WIPRO", "HCLTECH"],
        universe=None,
        universe_only=False,
        cap=3,
    )
    assert "^NSEI" not in out
    assert len(out) == 3


def test_rank_symbols_orders_most_mentioned_first():
    out = rank_symbols(
        ["INFY", "TCS", "TCS", "TCS", "INFY"],
        universe=None,
        universe_only=False,
        cap=2,
    )
    assert out[0] == "TCS"  # mentioned 3x beats INFY's 2x


def test_rank_symbols_universe_filter():
    out = rank_symbols(
        ["TCS", "INFY", "FOObar"],
        universe=["TCS", "INFY"],
        universe_only=True,
        cap=5,
    )
    assert out == ["INFY", "TCS"]  # FOOBAR dropped; alpha tie-break


def test_rank_symbols_zero_cap_is_empty():
    assert rank_symbols(["TCS"], universe_only=False, cap=0) == []


def test_rank_symbols_normalizes_case_and_blanks():
    out = rank_symbols(["tcs", "", "  ", "Tcs"], universe_only=False, cap=5)
    assert out == ["TCS"]


def test_symbol_cooldown_blocks_within_window_then_clears():
    cd = SymbolCooldown()
    assert cd.ready("TCS", 100.0, now=0.0) is True
    cd.mark("TCS", now=0.0)
    assert cd.ready("TCS", 100.0, now=50.0) is False   # still cooling
    assert cd.ready("TCS", 100.0, now=100.0) is True   # window elapsed
    assert cd.ready("infy", 100.0, now=50.0) is True   # unrelated symbol


def test_symbol_cooldown_zero_disables_gate():
    cd = SymbolCooldown()
    cd.mark("TCS", now=0.0)
    assert cd.ready("TCS", 0.0, now=0.0) is True


def test_symbol_cooldown_is_case_insensitive():
    cd = SymbolCooldown()
    cd.mark("TCS", now=0.0)
    assert cd.ready("tcs", 100.0, now=10.0) is False
