"""Fund-of-funds style allocator.

Converts a CIO proposal (a directional target weight + conviction) into a
desired whole-share position, sized with a fractional-Kelly ceiling derived
from conviction and capped at the per-position limit. The final clamp/veto is
done by the immutable guardrails - this only proposes a target.
"""

from __future__ import annotations

from quant.risk.sizing import fractional_kelly, kelly_fraction


def desired_target_qty(
    target_weight: float,
    conviction: float,
    equity: float,
    price: float,
    max_position_pct: float,
    kelly_fraction_scale: float = 0.5,
) -> int:
    if price <= 0 or equity <= 0:
        return 0
    # Treat conviction as edge: win prob in [0.5, 0.9]; symmetric payoff b=1.
    win_prob = 0.5 + 0.4 * max(0.0, min(1.0, conviction))
    full = kelly_fraction(win_prob, 1.0)             # = 0.8 * conviction
    half = max(0.0, fractional_kelly(full, kelly_fraction_scale))
    kelly_cap = min(half, max_position_pct)
    desired_weight = min(abs(target_weight), kelly_cap)
    # v1 is long-only: a negative target means "reduce toward zero".
    if target_weight < 0:
        return 0
    return int((desired_weight * equity) // price)
