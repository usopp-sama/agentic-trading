"""The four-state autonomy switch.

Resolves how a decision should be routed given the current mode, kill switch,
and the real-money gate:

  OFF      -> nothing executes.
  PAPER    -> paper broker, auto-commit.
  APPROVAL -> requires explicit human approval, then commits.
  AUTO     -> auto-commits.

``use_real`` is only ever True when the gate is open, mode is live, and the
kill switch is clear. In v1 the gate is disabled, so every route uses paper -
APPROVAL/AUTO run as "shadow real" until the gate opens.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Route:
    allowed: bool
    needs_approval: bool
    use_real: bool
    reason: str = ""


def resolve_route(mode: str, killed: bool, real_money_active: bool) -> Route:
    if killed:
        return Route(False, False, False, "kill switch engaged")
    if mode == "OFF":
        return Route(False, False, False, "mode OFF")
    if mode == "PAPER":
        return Route(True, False, False, "paper")
    if mode == "APPROVAL":
        return Route(True, True, real_money_active, "approval required")
    if mode == "AUTO":
        return Route(True, False, real_money_active, "auto")
    return Route(False, False, False, f"unknown mode {mode}")
