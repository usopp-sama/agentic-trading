"""Unit tests for the agentic trading server's safety-critical invariants.

These are pure-function tests (no network, no broker) covering the layers that
must never silently break: transaction fees, immutable guardrails, the autonomy
switch, the adaptive rule engine + meta-limits, position sizing, and the
hash-chained audit log.
"""

from __future__ import annotations

from ats.services.execution.autonomy import resolve_route
from ats.services.execution.fees import BROKERAGE_CAP, compute_charges
from ats.services.risk.guardrails import GuardrailInput, apply_guardrails
from ats.services.rules.engine import evaluate_rules, violates_meta_limits
from quant.risk.sizing import fractional_kelly, kelly_fraction, position_size


# --- fees ------------------------------------------------------------------
def test_buy_has_stamp_but_no_stt():
    c = compute_charges("BUY", 100, 50.0)
    assert c.stamp > 0
    assert c.stt == 0.0
    assert c.total > 0


def test_sell_has_stt_but_no_stamp():
    c = compute_charges("SELL", 100, 50.0)
    assert c.stt > 0
    assert c.stamp == 0.0


def test_brokerage_is_capped():
    c = compute_charges("BUY", 100000, 1000.0)  # huge turnover
    assert c.brokerage == BROKERAGE_CAP


# --- guardrails ------------------------------------------------------------
def _base_input(**overrides) -> GuardrailInput:
    base = dict(
        symbol="X", sector="IT", price=100.0, desired_target_qty=10_000,
        current_qty=0, equity=1_000_000.0, sector_value_excl_symbol=0.0,
        gross_value_excl_symbol=0.0, drawdown=0.0, max_position_pct=0.10,
        max_sector_pct=0.30, max_gross_pct=1.0, daily_loss_limit_pct=0.05,
        max_trade_value=1_000_000.0,
    )
    base.update(overrides)
    return GuardrailInput(**base)


def test_position_cap_clamps_quantity():
    # 10% of 1,000,000 / 100 = 1000 shares max
    res = apply_guardrails(_base_input(desired_target_qty=10_000))
    assert res.final_target_qty == 1000
    assert "max_position_pct" in res.applied


def test_daily_loss_breach_blocks_increase_and_demands_kill():
    res = apply_guardrails(_base_input(drawdown=-0.06, current_qty=500))
    assert res.kill is True
    # never allowed to increase exposure past current holdings
    assert res.final_target_qty <= 500
    assert res.side in {"HOLD", "SELL"}


def test_trade_value_cap_limits_delta():
    res = apply_guardrails(_base_input(desired_target_qty=500, max_trade_value=10_000))
    # delta notional capped at 10,000 / 100 = 100 shares
    assert res.delta_qty <= 100
    assert "max_trade_value" in res.applied


# --- autonomy switch -------------------------------------------------------
def test_kill_switch_blocks_everything():
    assert resolve_route("AUTO", killed=True, real_money_active=True).allowed is False


def test_off_blocks():
    assert resolve_route("OFF", killed=False, real_money_active=False).allowed is False


def test_paper_never_uses_real_money():
    r = resolve_route("PAPER", killed=False, real_money_active=True)
    assert r.allowed and not r.use_real and not r.needs_approval


def test_approval_requires_human():
    r = resolve_route("APPROVAL", killed=False, real_money_active=False)
    assert r.allowed and r.needs_approval


def test_auto_uses_real_only_when_gate_open():
    closed = resolve_route("AUTO", killed=False, real_money_active=False)
    open_ = resolve_route("AUTO", killed=False, real_money_active=True)
    assert closed.use_real is False
    assert open_.use_real is True


# --- adaptive rule engine + meta-limits ------------------------------------
def test_meta_limits_reject_guardrail_metric():
    reason = violates_meta_limits(
        {"metric": "position_pct", "op": "le", "value": 0.5, "action": "block"}
    )
    assert reason is not None


def test_meta_limits_reject_loosening_scale():
    reason = violates_meta_limits(
        {"metric": "rsi", "op": "gt", "value": 80, "action": "scale_size", "factor": 1.5}
    )
    assert reason is not None  # factor > 1 would *increase* size


def test_meta_limits_accept_conservative_rule():
    assert violates_meta_limits(
        {"metric": "rsi", "op": "gt", "value": 80, "action": "block"}
    ) is None


def test_rule_engine_blocks_and_scales():
    rules = [
        {"id": "ob", "expression": {"metric": "rsi", "op": "gt", "value": 80, "action": "block"}},
        {"id": "vol", "expression": {"metric": "vol_z", "op": "gt", "value": 3,
                                     "action": "scale_size", "factor": 0.5}},
    ]
    blocked = evaluate_rules(rules, {"rsi": 85, "vol_z": 1})
    assert blocked["block"] is True and "ob" in blocked["applied"]

    scaled = evaluate_rules(rules, {"rsi": 50, "vol_z": 4})
    assert scaled["block"] is False and scaled["scale"] == 0.5 and "vol" in scaled["applied"]

    clean = evaluate_rules(rules, {"rsi": 50, "vol_z": 1})
    assert clean["block"] is False and clean["scale"] == 1.0


# --- position sizing -------------------------------------------------------
def test_kelly_and_fractional_kelly():
    full = kelly_fraction(0.6, 2.0)  # edge present -> positive
    assert full > 0
    assert fractional_kelly(full, 0.5) == full * 0.5


def test_position_size_respects_max_fraction():
    qty = position_size(capital=1_000_000, fraction=0.9, price=100.0, max_fraction=0.25)
    # capped at 25% -> 250,000 / 100 = 2500 shares
    assert qty == 2500


# --- audit chain -----------------------------------------------------------
def test_audit_chain_is_tamper_evident():
    from ats.core import state
    from ats.core.db import init_db

    init_db()
    state.audit("tester", "unit.test.a", {"v": 1})
    state.audit("tester", "unit.test.b", {"v": 2})
    assert state.verify_audit_chain() is True
