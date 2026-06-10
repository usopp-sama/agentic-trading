"""Immutable, code-enforced guardrails.

These are the hard limits the agent can NEVER relax (defense in depth). They
clamp a desired target position down to what the rules allow, or veto it
entirely, and they can demand the global kill switch be engaged on a daily-loss
breach. Pure functions of numeric inputs so they are trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GuardrailInput:
    symbol: str
    sector: str
    price: float
    desired_target_qty: int
    current_qty: int
    equity: float
    sector_value_excl_symbol: float
    gross_value_excl_symbol: float
    drawdown: float  # negative number, e.g. -0.02
    max_position_pct: float
    max_sector_pct: float
    max_gross_pct: float
    daily_loss_limit_pct: float
    max_trade_value: float


@dataclass
class GuardrailResult:
    final_target_qty: int
    delta_qty: int
    side: str  # BUY/SELL/HOLD
    applied: list[str] = field(default_factory=list)
    vetoed: bool = False
    kill: bool = False


def apply_guardrails(g: GuardrailInput) -> GuardrailResult:
    applied: list[str] = []
    target = max(0, g.desired_target_qty)  # long-only

    # 1) Daily loss limit -> veto new risk + demand kill switch.
    kill = g.drawdown <= -abs(g.daily_loss_limit_pct)
    if kill:
        applied.append("daily_loss_limit")
        # Allow only reductions (sell toward zero), never increases.
        target = min(target, g.current_qty)

    # 2) Per-position cap.
    if g.price > 0 and g.equity > 0:
        max_pos_qty = int((g.max_position_pct * g.equity) // g.price)
        if target > max_pos_qty:
            target = max_pos_qty
            applied.append("max_position_pct")

    # 3) Sector cap.
    if g.price > 0 and g.equity > 0:
        allowed_sector_value = g.max_sector_pct * g.equity
        max_symbol_value = max(0.0, allowed_sector_value - g.sector_value_excl_symbol)
        max_sector_qty = int(max_symbol_value // g.price)
        if target > max_sector_qty:
            target = max_sector_qty
            applied.append("max_sector_pct")

    # 4) Gross exposure cap (no leverage).
    if g.price > 0 and g.equity > 0:
        allowed_gross_value = g.max_gross_pct * g.equity
        max_symbol_value = max(0.0, allowed_gross_value - g.gross_value_excl_symbol)
        max_gross_qty = int(max_symbol_value // g.price)
        if target > max_gross_qty:
            target = max_gross_qty
            applied.append("max_gross_pct")

    # 5) Per-order notional cap on the delta.
    delta = target - g.current_qty
    if g.price > 0 and abs(delta) * g.price > g.max_trade_value:
        max_delta_qty = int(g.max_trade_value // g.price)
        delta = max_delta_qty if delta > 0 else -max_delta_qty
        target = g.current_qty + delta
        applied.append("max_trade_value")

    side = "BUY" if delta > 0 else "SELL" if delta < 0 else "HOLD"
    vetoed = delta == 0 and target != g.current_qty
    return GuardrailResult(
        final_target_qty=target,
        delta_qty=delta,
        side=side,
        applied=applied,
        vetoed=(side == "HOLD"),
        kill=kill,
    )
