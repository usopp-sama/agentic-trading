"""CIO aggregator.

Combines SME opinions into a single, ranked proposed position. Aggregation is
deterministic and auditable: a weighted average of each SME's directional view
(stance x conviction) using effective weights (persona base weight x learned
vote weight), plus an optional macro regime tilt from Family B. RISK-family
personas are excluded from direction (they only clamp later).

The CIO does not size for real risk - that is the Risk Manager's job (Phase 6).
It outputs a target tilt; the allocator and guardrails convert it to quantity.
"""

from __future__ import annotations

from ats.core.logging import get_logger
from ats.core.schemas import Opinion, ProposedPosition

log = get_logger("ats.cio")

_ACTION_THRESHOLD = 0.15


class CIO:
    def __init__(self, max_weight: float = 0.10, macro_gain: float = 0.3) -> None:
        self.max_weight = max_weight
        self.macro_gain = macro_gain

    def aggregate(
        self,
        symbol: str,
        opinions: list[Opinion],
        weights: dict[str, float],
        macro_tilt: float = 0.0,
    ) -> ProposedPosition:
        num = 0.0
        den = 0.0
        contributors: dict[str, dict] = {}
        for op in opinions:
            w = float(weights.get(op.sme, 0.0))
            direction = op.stance.direction / 2.0  # map -2..2 -> -1..1
            contribution = w * direction * op.conviction
            num += contribution
            den += w
            contributors[op.sme] = {
                "stance": op.stance.value,
                "conviction": round(op.conviction, 3),
                "weight": round(w, 3),
                "contribution": round(contribution, 4),
            }

        base = (num / den) if den > 0 else 0.0
        net = max(-1.0, min(1.0, base + self.macro_gain * macro_tilt))

        if net >= _ACTION_THRESHOLD:
            action = "BUY"
        elif net <= -_ACTION_THRESHOLD:
            action = "SELL"
        else:
            action = "HOLD"

        top = sorted(contributors.items(), key=lambda kv: -abs(kv[1]["contribution"]))[:3]
        top_txt = ", ".join(f"{k}({v['stance']})" for k, v in top) or "no active voters"
        rationale = (
            f"CIO net tilt {net:+.2f} on {symbol} (macro_tilt {macro_tilt:+.2f}); "
            f"top contributors: {top_txt}."
        )
        return ProposedPosition(
            symbol=symbol,
            action=action,
            target_weight=round(net * self.max_weight, 4),
            conviction=round(abs(net), 3),
            rationale=rationale,
            contributors=contributors,
        )
