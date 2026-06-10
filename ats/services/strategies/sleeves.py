"""Virtual capital sleeves: per-strategy P&L attribution + decay detection.

Each strategy gets a virtual book that holds, equal-weighted, every
symbol the strategy is currently bullish on. Books are marked to market
close-to-close and are look-ahead safe: today's bar P&L accrues to the
holdings decided on *previous* bars; signal updates from today's bar
only affect tomorrow's P&L (the same one-bar discipline as the
backtester).

This answers two questions the blended real book cannot:
- attribution: which strategy is actually earning its keep?
- decay: has a strategy's rolling Sharpe fallen below what we tolerate?

Pure in-memory state machine; persistence of finalized days is the
caller's job (see ``StrategyService``), which keeps this trivially
testable.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from datetime import date

TRADING_DAYS = 252
_HISTORY_DAYS = 250


@dataclass
class SleeveBook:
    strategy: str
    holdings: set[str] = field(default_factory=set)
    equity: float = 1.0
    day_return: float = 0.0
    daily_returns: deque[float] = field(default_factory=lambda: deque(maxlen=_HISTORY_DAYS))
    peak_equity: float = 1.0
    last_alert_day: date | None = None


@dataclass(frozen=True)
class FinalizedDay:
    strategy: str
    day: date
    ret: float
    equity: float
    holdings: int
    decayed: bool  # rolling Sharpe below threshold -> caller should alert


class SleeveTracker:
    def __init__(
        self,
        decay_sharpe: float = 0.0,
        decay_min_days: int = 60,
        sharpe_window: int = 60,
    ) -> None:
        self._books: dict[str, SleeveBook] = {}
        self._last_close: dict[str, float] = {}
        self._current_day: date | None = None
        self._decay_sharpe = decay_sharpe
        self._decay_min_days = decay_min_days
        self._sharpe_window = sharpe_window

    def _book(self, strategy: str) -> SleeveBook:
        if strategy not in self._books:
            self._books[strategy] = SleeveBook(strategy=strategy)
        return self._books[strategy]

    # --- marking ------------------------------------------------------------
    def mark_bar(self, symbol: str, close: float, day: date) -> list[FinalizedDay]:
        """Mark all books holding ``symbol`` with its close-to-close return.

        Must be called BEFORE strategies are re-evaluated on this bar, so
        the return accrues to yesterday's holdings (no look-ahead). When
        the calendar advances, every book's previous day is finalized
        first and returned for persistence.
        """
        finalized: list[FinalizedDay] = []
        if self._current_day is None:
            self._current_day = day
        elif day > self._current_day:
            finalized = self._finalize_day(self._current_day)
            self._current_day = day

        prev = self._last_close.get(symbol)
        self._last_close[symbol] = close
        if prev is None or prev <= 0 or close <= 0:
            return finalized

        bar_ret = close / prev - 1.0
        for book in self._books.values():
            if symbol in book.holdings:
                # Equal-weight across the names held by this sleeve.
                book.day_return += bar_ret / max(1, len(book.holdings))
        return finalized

    def update_holding(self, strategy: str, symbol: str, direction: int) -> None:
        """Set a sleeve's stance on a symbol (long-only: >0 holds, else flat)."""
        book = self._book(strategy)
        if direction > 0:
            book.holdings.add(symbol)
        else:
            book.holdings.discard(symbol)

    def _finalize_day(self, day: date) -> list[FinalizedDay]:
        out: list[FinalizedDay] = []
        for book in self._books.values():
            book.daily_returns.append(book.day_return)
            book.equity *= 1.0 + book.day_return
            book.peak_equity = max(book.peak_equity, book.equity)
            decayed = self._is_decayed(book) and book.last_alert_day != day
            if decayed:
                book.last_alert_day = day
            out.append(
                FinalizedDay(
                    strategy=book.strategy,
                    day=day,
                    ret=book.day_return,
                    equity=book.equity,
                    holdings=len(book.holdings),
                    decayed=decayed,
                )
            )
            book.day_return = 0.0
        return out

    # --- analytics ------------------------------------------------------------
    def _is_decayed(self, book: SleeveBook) -> bool:
        if len(book.daily_returns) < self._decay_min_days:
            return False
        sharpe = self.rolling_sharpe(book.strategy)
        return sharpe is not None and sharpe < self._decay_sharpe

    def returns_by_sleeve(self) -> dict[str, list[float]]:
        """Daily return history per sleeve (input to capital allocation)."""
        return {sid: list(b.daily_returns) for sid, b in self._books.items()}

    def rolling_sharpe(self, strategy: str) -> float | None:
        book = self._books.get(strategy)
        if book is None or len(book.daily_returns) < 20:
            return None
        rets = list(book.daily_returns)[-self._sharpe_window:]
        n = len(rets)
        mean = sum(rets) / n
        var = sum((r - mean) ** 2 for r in rets) / (n - 1) if n > 1 else 0.0
        if var <= 0:
            return 0.0
        return mean / math.sqrt(var) * math.sqrt(TRADING_DAYS)

    def max_drawdown(self, strategy: str) -> float:
        """Worst peak-to-trough decline of the sleeve's equity curve, <= 0."""
        book = self._books.get(strategy)
        if book is None:
            return 0.0
        equity, peak, worst = 1.0, 1.0, 0.0
        for r in book.daily_returns:
            equity *= 1.0 + r
            peak = max(peak, equity)
            worst = min(worst, equity / peak - 1.0)
        return worst

    def stats(self) -> list[dict]:
        out = []
        for sid in sorted(self._books):
            book = self._books[sid]
            sharpe = self.rolling_sharpe(sid)
            out.append(
                {
                    "strategy": sid,
                    "equity": round(book.equity, 4),
                    "days": len(book.daily_returns),
                    "holdings": sorted(book.holdings),
                    "sharpe": round(sharpe, 2) if sharpe is not None else None,
                    "max_drawdown": round(self.max_drawdown(sid), 4),
                }
            )
        return out
