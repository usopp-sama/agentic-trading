"""Rule evaluation + meta-limits.

Two classes of rules:
- Guardrails: immutable, human-only, enforced in code by the Risk Manager.
- Adaptive rules: agent-proposable filters that can only make the system MORE
  conservative (block or shrink). Meta-limits forbid an adaptive rule from
  touching a guardrail metric or from loosening anything.

Adaptive rule expression schema:
    {metric, op (gt|lt|ge|le), value, action (block|scale_size), factor?}
"""

from __future__ import annotations

# Metrics that only humans may govern; adaptive rules may not target them.
PROTECTED_METRICS = {
    "position_pct", "sector_pct", "daily_loss_pct",
    "gross_exposure_pct", "trade_value",
}

_OPS = {
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "ge": lambda a, b: a >= b,
    "le": lambda a, b: a <= b,
}


def violates_meta_limits(expression: dict) -> str | None:
    """Return a reason string if the proposed adaptive rule is illegal."""
    metric = expression.get("metric")
    if metric in PROTECTED_METRICS:
        return f"adaptive rules may not govern guardrail metric '{metric}'"
    if expression.get("action") not in {"block", "scale_size"}:
        return "adaptive rules may only 'block' or 'scale_size' (be more conservative)"
    if expression.get("action") == "scale_size":
        factor = float(expression.get("factor", 1.0))
        if not (0.0 < factor < 1.0):
            return "scale_size factor must be in (0,1) - rules can only shrink"
    if expression.get("op") not in _OPS:
        return f"unknown op '{expression.get('op')}'"
    return None


def evaluate_rules(active_rules: list[dict], context: dict) -> dict:
    """Apply active adaptive rules to a decision context.

    Returns {"block": bool, "scale": float, "applied": [rule_ids]}.
    """
    block = False
    scale = 1.0
    applied: list[str] = []
    for rule in active_rules:
        expr = rule.get("expression", {})
        metric = expr.get("metric")
        op = _OPS.get(expr.get("op", ""))
        if metric is None or op is None or metric not in context:
            continue
        if op(context[metric], expr.get("value")):
            applied.append(rule.get("id", "?"))
            if expr.get("action") == "block":
                block = True
            elif expr.get("action") == "scale_size":
                scale *= float(expr.get("factor", 1.0))
    return {"block": block, "scale": round(scale, 4), "applied": applied}
