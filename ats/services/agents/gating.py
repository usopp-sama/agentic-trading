"""Autonomous-evaluation gating: keep Gemini spend predictable.

Small, testable helpers that decide *whether* and *which* symbols an autonomous
trigger (fresh news sentiment, a volume spike, the periodic macro sweep) is
allowed to spend LLM tokens on. The user-driven paths (Experts console, Today
brief) bypass these entirely -- if you click it, it runs.

Three levers, all config-driven (see ``ats.core.config``):

1. ``eval_window_open``  -- clock gate; no autonomous spend outside the session.
2. ``SymbolCooldown``    -- per-symbol debounce so a news burst on one name
                            costs one evaluation, not one per item.
3. ``rank_symbols``      -- universe filter + most-mentioned ordering + a cap on
                            how many names a single event fans out to.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from datetime import datetime


def eval_window_open(now: datetime | None = None) -> bool:
    """True when autonomous LLM evaluation is permitted by the clock.

    Honors ``llm_eval_market_hours_only``: when set, autonomous SME/macro work
    only runs inside the NSE session plus the post-close grace window. News and
    sentiment are still collected and scored locally outside this window.
    """
    from ats.core.config import get_settings
    from ats.services.market_data.calendar import is_polling_window

    if not get_settings().llm_eval_market_hours_only:
        return True
    return is_polling_window(now)


class SymbolCooldown:
    """Per-symbol monotonic-clock cooldown.

    ``ready(symbol, cooldown_s)`` reports whether ``symbol`` may be evaluated
    again; call ``mark(symbol)`` once an evaluation is actually dispatched. A
    cooldown of 0 disables the gate (always ready).
    """

    def __init__(self) -> None:
        self._last: dict[str, float] = {}

    def ready(self, symbol: str, cooldown_s: float, *, now: float | None = None) -> bool:
        if cooldown_s <= 0:
            return True
        t = time.monotonic() if now is None else now
        last = self._last.get(symbol.upper())
        return last is None or (t - last) >= cooldown_s

    def mark(self, symbol: str, *, now: float | None = None) -> None:
        self._last[symbol.upper()] = time.monotonic() if now is None else now


def rank_symbols(
    tickers: Iterable[str],
    *,
    universe: Iterable[str] | None = None,
    universe_only: bool = True,
    cap: int = 3,
) -> list[str]:
    """Order and trim the symbols a single event should fan out to.

    - drops index/benchmark tickers (``^NSEI`` etc.) -- those drive the macro
      view, not a per-symbol SME pass;
    - de-dupes, ranking most-mentioned first (ties broken alphabetically) so a
      headline genuinely about one name beats incidental mentions;
    - optionally keeps only names in our active ``universe``;
    - caps the result to ``cap`` symbols (``cap <= 0`` -> empty).
    """
    counts: dict[str, int] = {}
    for raw in tickers:
        if not raw:
            continue
        sym = str(raw).strip().upper()
        if not sym or sym.startswith("^"):
            continue
        counts[sym] = counts.get(sym, 0) + 1

    ordered = sorted(counts, key=lambda k: (-counts[k], k))
    if universe_only and universe is not None:
        uni = {str(u).strip().upper() for u in universe}
        ordered = [s for s in ordered if s in uni]
    if cap <= 0:
        return []
    return ordered[:cap]
