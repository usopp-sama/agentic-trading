"""Scoring math for SME track records.

- hit-rate: fraction of directional calls that matched the forward return.
- Brier score: mean squared error of (conviction-as-probability) vs outcome.
- vote weight: a bounded function of hit-rate so good SMEs gain influence and
  poor ones lose it, without ever going to zero or unbounded.
"""

from __future__ import annotations


def update_record(
    *,
    n: int,
    wins: int,
    brier_sum: float,
    pnl_contrib: float,
    correct: bool,
    conviction: float,
    contribution_return: float,
) -> dict:
    """Return updated running stats given one resolved call.

    ``brier_sum`` is the accumulated squared error; we store the mean as
    ``brier`` but keep the sum implicitly via n for incremental updates.
    """
    new_n = n + 1
    new_wins = wins + (1 if correct else 0)
    hit_rate = new_wins / new_n
    outcome = 1.0 if correct else 0.0
    # Incremental Brier: recompute mean from previous mean.
    prev_mean = brier_sum  # we pass current mean in as brier_sum
    se = (conviction - outcome) ** 2
    brier = (prev_mean * n + se) / new_n
    new_pnl = pnl_contrib + contribution_return
    vote_weight = max(0.1, min(2.0, 0.25 + (hit_rate - 0.5) * 1.5))
    return {
        "n": new_n,
        "wins": new_wins,
        "hit_rate": round(hit_rate, 4),
        "brier": round(brier, 4),
        "pnl_contrib": round(new_pnl, 4),
        "vote_weight": round(vote_weight, 4),
    }


def promotion_decision(n: int, hit_rate: float, status: str) -> tuple[str, float]:
    """Return (new_status, promoted_weight) given a track record.

    Gates: need a minimum sample. Promote shadow -> active on good hit-rate;
    demote active -> shadow on poor hit-rate. Hysteresis avoids flip-flopping.
    """
    MIN_N = 12
    if n < MIN_N:
        return status, 0.0 if status == "shadow" else 0.5
    if status == "shadow" and hit_rate >= 0.55:
        return "active", 0.5
    if status == "active" and hit_rate <= 0.40:
        return "shadow", 0.0
    return status, (0.5 if status == "active" else 0.0)
