"""Vol-Premium Service — the final roadmap sleeve (7.7), built last on purpose.

Sells an iron condor on NIFTY when implied volatility is rich versus
realized (the documented volatility risk premium), using the options
paper book. The roadmap's hard rules are enforced in code, not policy:

- **Defined-risk only**: the book can only open credit spreads whose
  worst case is reserved as margin up front. Naked anything is
  unrepresentable.
- **Small sleeve**: capital is the configured sleeve budget (~10% of
  the paper book), not the whole account.
- **Never in crisis**: entries are blocked when the regime service
  reads crisis volatility, when the kill switch is engaged, or when the
  trading mode is OFF.
- **Paper only**: this service has no real-broker path at all.

Entry: IV premium (ATM IV − 20d realized) >= threshold → sell a condor
with short strikes ~5% OTM and wings a few strike-steps further out,
priced via Black-Scholes at the chain's ATM IV.
Exits: 50% of credit captured (profit target), debit at 2× credit
(stop), or expiry settlement — whichever comes first.

Daily sleeve P&L is persisted to ``SleevePnl`` under ``vol_premium`` so
attribution and the dashboard treat it like every other sleeve.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import SleevePnl
from ats.services.execution.options_book import OptionsPaperBook
from quant.options import bs_price

log = get_logger("ats.vol_premium")

SLEEVE_ID = "vol_premium"
_RISK_FREE = 0.065


# --- pure decision rules ------------------------------------------------------
def should_enter(
    iv_premium: float | None,
    threshold: float,
    has_open: bool,
    crisis: bool,
    killed: bool,
    mode: str,
) -> bool:
    """All of: rich IV, flat book, calm regime, live system."""
    if iv_premium is None or has_open or crisis or killed or mode == "OFF":
        return False
    return iv_premium >= threshold


def exit_reason(
    entry_credit: float, current_debit: float, profit_target: float, stop_mult: float
) -> str | None:
    """'profit_target' | 'stop' | None while the trade is working."""
    if current_debit <= entry_credit * (1.0 - profit_target):
        return "profit_target"
    if current_debit >= entry_credit * stop_mult:
        return "stop"
    return None


def condor_strikes(spot: float, otm_pct: float, step: float, wing_steps: int) -> dict:
    """Short strikes ~otm_pct away rounded to the strike grid, wings beyond.

    When the grid is coarse relative to the spot (e.g. synthetic data at
    index level ~300 with a 50-point step), naive rounding can swallow
    the OTM offset and put a short strike AT the money — so each short
    strike is forced at least one full step beyond spot on its own side.
    """
    atm = round(spot / step) * step
    short_call = max(round(spot * (1.0 + otm_pct) / step) * step, atm + step)
    short_put = min(round(spot * (1.0 - otm_pct) / step) * step, atm - step)
    return {
        "short_call": short_call,
        "long_call": short_call + wing_steps * step,
        "short_put": short_put,
        "long_put": short_put - wing_steps * step,
    }


def price_condor_credit(
    spot: float, strikes: dict, iv: float, t_years: float, r: float = _RISK_FREE
) -> dict:
    """Per-unit credits for both legs at a flat IV (paper approximation)."""
    call_credit = bs_price(spot, strikes["short_call"], t_years, r, iv, "call") - bs_price(
        spot, strikes["long_call"], t_years, r, iv, "call"
    )
    put_credit = bs_price(spot, strikes["short_put"], t_years, r, iv, "put") - bs_price(
        spot, strikes["long_put"], t_years, r, iv, "put"
    )
    return {"call": max(0.0, call_credit), "put": max(0.0, put_credit)}


def viable_credit(credit: float, wing_width: float, min_frac: float = 0.02) -> bool:
    """A leg is worth selling only if the credit is a meaningful fraction
    of the width at risk — otherwise the trade reserves near-full margin
    to collect noise (the zero-credit-far-OTM failure mode)."""
    return wing_width > 0 and credit >= min_frac * wing_width


class VolPremiumService:
    name = "vol_premium"

    def __init__(self) -> None:
        settings = get_settings()
        self.book = OptionsPaperBook(capital=settings.vol_sleeve_capital)
        self._bus: EventBus | None = None
        self._regime = None
        self._last_mark: dict | None = None
        self._last_pnl_day: date | None = None
        self._prev_equity: float | None = None

    _STATE_KEY = "vol_premium:book"

    async def start(self, ctx) -> None:
        if not get_settings().vol_premium_enabled:
            log.info("vol_premium_disabled")
            return
        self._bus = ctx.bus
        self._regime = ctx.orchestrator.get("regime")
        # Reload any open spreads + sleeve P&L state so a restart does not drop
        # live option positions or double-count daily P&L.
        self._restore_state()
        ctx.bus.subscribe(Topic.OPTION_CHAIN, self._on_chain)

    def _restore_state(self) -> None:
        saved = state.get_kv(self._STATE_KEY, {})
        if not saved:
            return
        try:
            self.book.load_state(saved)
            pd = saved.get("last_pnl_day")
            self._last_pnl_day = date.fromisoformat(pd) if pd else None
            self._prev_equity = saved.get("prev_equity")
            log.info("vol_premium_state_restored", extra={"open": len(self.book.open_spreads())})
        except Exception as exc:  # noqa: BLE001 - corrupt state must not block boot
            log.warning("vol_premium_state_restore_failed", extra={"error": str(exc)})

    def _persist_state(self) -> None:
        payload = self.book.export_state()
        payload["prev_equity"] = self._prev_equity
        payload["last_pnl_day"] = self._last_pnl_day.isoformat() if self._last_pnl_day else None
        state.set_kv(self._STATE_KEY, payload)

    # --- the cycle: every option-chain snapshot drives the sleeve --------------
    async def _on_chain(self, evt) -> None:
        try:
            await self.process_snapshot(evt.payload)
        except Exception as exc:  # noqa: BLE001 - sleeve errors must not kill the bus
            log.warning("vol_premium_error", extra={"error": str(exc)})

    async def process_snapshot(self, snap: dict) -> None:
        settings = get_settings()
        spot = float(snap.get("spot") or 0.0)
        iv = float(snap.get("atm_iv") or 0.0)
        if spot <= 0 or iv <= 0:
            return
        expiry = date.fromisoformat(snap["expiry"])
        today = datetime.now(timezone.utc).date()
        t_years = max((expiry - today).days, 0) / 365.0
        self._last_mark = {"spot": spot, "iv": iv, "t_years": t_years}

        # 1) Expiry settlement first.
        for spread in self.book.settle_expired(spot, today):
            self._log_close(spread)

        # 2) Manage open spreads against profit target / stop.
        for spread in list(self.book.open_spreads()):
            debit = spread.value_to_close(spot, iv, t_years, _RISK_FREE)
            reason = exit_reason(
                spread.entry_credit, debit,
                settings.vol_profit_target, settings.vol_stop_mult,
            )
            if reason:
                self.book.close_spread(spread.spread_id, debit, reason)
                self._log_close(spread)

        # 3) Entry.
        crisis = bool(self._regime.is_crisis()) if self._regime is not None else False
        if should_enter(
            snap.get("iv_premium"), settings.vol_entry_iv_premium,
            has_open=bool(self.book.open_spreads()),
            crisis=crisis, killed=state.is_killed(), mode=state.get_mode(),
        ):
            self._open_condor(snap, spot, iv, expiry, t_years)

        # 4) Daily sleeve P&L row.
        self._record_daily(today, spot, iv, t_years)

        # 5) Persist the book + sleeve state so a restart resumes cleanly.
        self._persist_state()

    def _open_condor(self, snap: dict, spot: float, iv: float, expiry: date, t_years: float) -> None:
        settings = get_settings()
        strikes = condor_strikes(
            spot, settings.vol_otm_pct, settings.nifty_strike_step, settings.vol_wing_steps
        )
        credits = price_condor_credit(spot, strikes, iv, max(t_years, 1 / 365.0))
        wing_width = settings.vol_wing_steps * settings.nifty_strike_step
        if not (viable_credit(credits["call"], wing_width) or viable_credit(credits["put"], wing_width)):
            log.info(
                "vol_premium_entry_skipped",
                extra={"reason": "credit too thin for width", "credits": credits},
            )
            return
        opened = []
        try:
            if viable_credit(credits["call"], wing_width):
                opened.append(self.book.open_spread(
                    snap.get("symbol", "NIFTY"), "CE",
                    strikes["short_call"], strikes["long_call"], expiry,
                    settings.vol_max_lots, settings.nifty_lot_size, credits["call"],
                ))
            if viable_credit(credits["put"], wing_width):
                opened.append(self.book.open_spread(
                    snap.get("symbol", "NIFTY"), "PE",
                    strikes["short_put"], strikes["long_put"], expiry,
                    settings.vol_max_lots, settings.nifty_lot_size, credits["put"],
                ))
        except ValueError as exc:
            log.info("vol_premium_entry_skipped", extra={"reason": str(exc)})
            return
        if opened:
            total_credit = sum(s.entry_credit * s.units for s in opened)
            state.audit(SLEEVE_ID, "options.open_condor", {
                "expiry": expiry.isoformat(), "strikes": strikes,
                "credit": round(total_credit, 2),
                "margin": round(self.book.margin_reserved(), 2),
                "iv": iv, "iv_premium": snap.get("iv_premium"),
            })
            log.info("vol_premium_opened", extra={"strikes": strikes, "credit": round(total_credit, 2)})

    def _log_close(self, spread) -> None:
        state.audit(SLEEVE_ID, "options.close_spread", {
            "spread_id": spread.spread_id, "kind": spread.kind,
            "reason": spread.close_reason, "pnl": round(spread.realized(), 2),
        })
        log.info("vol_premium_closed", extra={
            "spread_id": spread.spread_id, "reason": spread.close_reason,
            "pnl": round(spread.realized(), 2),
        })

    # --- sleeve P&L persistence -----------------------------------------------------
    def _record_daily(self, today: date, spot: float, iv: float, t_years: float) -> None:
        equity = self.book.equity(spot, iv, t_years)
        if self._last_pnl_day == today:
            return
        prev = self._prev_equity if self._prev_equity is not None else self.book.capital
        ret = (equity - prev) / self.book.capital if self.book.capital else 0.0
        with session_scope() as s:
            row = s.execute(
                select(SleevePnl).where(SleevePnl.strategy == SLEEVE_ID, SleevePnl.day == today)
            ).scalar_one_or_none()
            if row is None:
                row = SleevePnl(strategy=SLEEVE_ID, day=today)
                s.add(row)
            row.ret = round(ret, 6)
            row.equity = round(equity / self.book.capital, 6)
            row.holdings = len(self.book.open_spreads())
        self._last_pnl_day = today
        self._prev_equity = equity

    # --- dashboard ---------------------------------------------------------------------
    def book_stats(self) -> dict:
        if self._last_mark is None:
            return self.book.stats()
        return self.book.stats(
            spot=self._last_mark["spot"], iv=self._last_mark["iv"],
            t_years=self._last_mark["t_years"],
        )
