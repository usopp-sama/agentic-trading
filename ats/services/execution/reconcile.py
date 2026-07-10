"""Reconciliation: internal book vs broker/ledger truth.

The single component that prevents the classic account-blowing failure mode
of home-built systems — internal state drift. Periodically (daily in paper,
every few minutes in live) it cross-checks, per account:

1. **positions vs fills** — replaying every fill (with the same long-only
   sell clamp the portfolio applies) must land exactly on the positions table;
2. **ledger journal integrity** — each passbook entry's running balance must
   equal the previous balance plus the entry, and the final row must equal
   the live balance;
3. **ledger vs legacy cash** — the ``cash:<account>`` mirror the dashboards
   read must match the ledger cash to the paisa;
4. **broker vs ledger** — the broker's ``margins()`` must agree with the
   ledger (trivially true for BrokerSim; the real check when Kite arrives).

Any mismatch beyond rounding → **halt new entries + alert**; a human
resolves and releases. Engage-only-auto, release-only-human — the same
principle as every other kill switch here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.core.models import Fill, LedgerEntry, Order, Position
from ats.services.accounts.ledger import AccountLedger

log = get_logger("ats.reconcile")

HALT_KEY = "recon:halt"
LAST_KEY = "recon:last"
_TOL = 0.05  # rupees of float rounding we forgive


def check_positions_vs_fills(account: str) -> list[str]:
    """Replay every fill; the result must equal the positions table exactly."""
    mismatches: list[str] = []
    with session_scope() as s:
        rows = s.execute(
            select(Order.symbol, Order.side, Fill.qty)
            .join(Fill, Fill.order_id == Order.id)
            .where(Order.account == account)
            .order_by(Fill.id)
        ).all()
        replayed: dict[str, int] = {}
        for symbol, side, qty in rows:
            held = replayed.get(symbol, 0)
            if side == "BUY":
                replayed[symbol] = held + qty
            else:  # same long-only clamp as portfolio.apply_fill
                replayed[symbol] = held - min(qty, held)
        positions = {
            p.symbol: p.qty
            for p in s.execute(
                select(Position).where(Position.account == account)
            ).scalars().all()
        }
    for symbol in sorted(set(replayed) | set(positions)):
        want = replayed.get(symbol, 0)
        have = positions.get(symbol, 0)
        if want != have:
            mismatches.append(
                f"{account}/{symbol}: fills replay to {want}, positions say {have}"
            )
    return mismatches


def check_ledger_journal(account: str) -> list[str]:
    """Walk the passbook oldest-first: running balances must chain exactly,
    and the last row must equal the live balance."""
    mismatches: list[str] = []
    with session_scope() as s:
        entries = s.execute(
            select(LedgerEntry)
            .where(LedgerEntry.account == account)
            .order_by(LedgerEntry.ts, LedgerEntry.id)
        ).scalars().all()
        rows = [
            (e.kind, e.amount, e.reserved_delta, e.cash_after, e.reserved_after)
            for e in entries
        ]
    if not rows:
        return mismatches
    cash, reserved = 0.0, 0.0
    for i, (kind, amount, r_delta, cash_after, reserved_after) in enumerate(rows):
        cash = round(cash + amount, 2)
        reserved = round(reserved + r_delta, 2)
        if abs(cash - cash_after) > _TOL:
            mismatches.append(
                f"{account}: journal row {i} ({kind}) cash chain {cash} != recorded {cash_after}"
            )
            cash = cash_after  # resync so one break reports once
        if abs(reserved - reserved_after) > _TOL:
            mismatches.append(
                f"{account}: journal row {i} ({kind}) reserved chain {reserved} != recorded {reserved_after}"
            )
            reserved = reserved_after
    bal = AccountLedger(account).balance()
    if abs(bal.cash - rows[-1][3]) > _TOL:
        mismatches.append(
            f"{account}: live cash {bal.cash} != last journal balance {rows[-1][3]}"
        )
    return mismatches


def check_ledger_vs_legacy_cash(account: str) -> list[str]:
    from ats.services.execution.portfolio import get_cash

    ledger_cash = AccountLedger(account).balance().cash
    legacy = get_cash(account)
    if abs(ledger_cash - legacy) > _TOL:
        return [f"{account}: ledger cash {ledger_cash} != legacy cash key {legacy}"]
    return []


def check_broker_vs_ledger(account: str, broker) -> list[str]:
    if broker is None:
        return []
    margins = broker.margins(account)
    bal = AccountLedger(account).balance()
    if abs(margins.get("cash", 0.0) - bal.cash) > _TOL:
        return [f"{account}: broker cash {margins.get('cash')} != ledger {bal.cash}"]
    return []


def reconcile_account(account: str, ledger_backed: bool = True, broker=None) -> dict:
    mismatches = check_positions_vs_fills(account)
    # P2: the demat (depository) leg must equal broker positions per symbol.
    try:
        from ats.services.accounts.demat import check_positions_vs_demat

        mismatches += check_positions_vs_demat(account)
    except Exception as exc:  # noqa: BLE001 — demat check must not crash recon
        mismatches.append(f"{account}: demat check failed: {exc}")
    if ledger_backed:
        mismatches += check_ledger_journal(account)
        mismatches += check_ledger_vs_legacy_cash(account)
        mismatches += check_broker_vs_ledger(account, broker)
    return {"account": account, "ok": not mismatches, "mismatches": mismatches}


def entries_halted() -> bool:
    return bool(state.get_kv(HALT_KEY).get("engaged"))


class ReconciliationService:
    name = "reconcile"

    def __init__(self) -> None:
        self._bus = None
        self._orch = None

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._orch = ctx.orchestrator
        settings = get_settings()
        from ats.services.market_data.calendar import IST

        ctx.scheduler.add_job(
            self.run_sync, "cron",
            hour=settings.recon_hour, minute=settings.recon_minute, timezone=IST,
            id="reconcile_daily", max_instances=1, coalesce=True,
        )
        # P2: T+1 demat settlement — once daily, post-close, before recon so the
        # depository holdings settle overnight like real Indian T+1.
        ctx.scheduler.add_job(
            self._settle_demat, "cron", hour=16, minute=30, timezone=IST,
            id="demat_settle_daily", max_instances=1, coalesce=True,
        )
        if settings.recon_interval_s > 0:
            ctx.scheduler.add_job(
                self.run_sync, "interval", seconds=settings.recon_interval_s,
                id="reconcile_interval", max_instances=1, coalesce=True,
            )
        log.info("reconcile_started", extra={"halted": entries_halted()})

    def _settle_demat(self) -> int:
        """Daily T+1 demat settlement across all profiles (P2)."""
        from ats.services.accounts.demat import settle_pending

        return settle_pending()

    # --- the run ---------------------------------------------------------------
    def _accounts(self) -> list[tuple[str, bool]]:
        """(account, ledger_backed) for everything we can check."""
        out: list[tuple[str, bool]] = [("paper", False)]  # main combined book
        league = self._orch.get("league") if self._orch else None
        if league is not None and hasattr(league, "accounts"):
            out += [(a, True) for a in league.accounts()]
        return out

    def run_sync(self) -> dict:
        results = []
        league = self._orch.get("league") if self._orch else None
        broker = getattr(league, "_broker", None)
        for account, ledger_backed in self._accounts():
            try:
                results.append(reconcile_account(account, ledger_backed, broker))
            except Exception as exc:  # noqa: BLE001 — one broken account must not
                results.append({"account": account, "ok": False,   # hide the rest
                                "mismatches": [f"reconcile crashed: {exc}"]})
        mismatches = [m for r in results for m in r["mismatches"]]
        report = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "ok": not mismatches,
            "accounts": len(results),
            "mismatches": mismatches,
        }
        state.set_kv(LAST_KEY, report)
        if mismatches:
            self._halt(mismatches)
        log.info("reconcile_run",
                 extra={"ok": report["ok"], "accounts": len(results),
                        "mismatches": len(mismatches)})
        return report

    def _halt(self, mismatches: list[str]) -> None:
        already = entries_halted()
        state.set_kv(HALT_KEY, {
            "engaged": True,
            "ts": datetime.now(timezone.utc).isoformat(),
            "mismatches": mismatches[:20],
        })
        if not already:
            state.audit("reconcile", "recon.halt", {"mismatches": mismatches[:20]})
            from ats.services.execution.notify import notify

            notify(
                "RECONCILIATION MISMATCH — new entries halted until you review: "
                + "; ".join(mismatches[:5])
            )
            if self._bus is not None:
                import asyncio

                try:
                    asyncio.get_running_loop()
                    asyncio.create_task(self._bus.publish(
                        Topic.ALERT,
                        {"kind": "reconcile", "mismatches": mismatches[:10],
                         "message": "Book/broker mismatch — entries halted."},
                    ))
                except RuntimeError:
                    pass  # no loop (sync test context) — kv + notify already done

    def release(self, actor: str = "human") -> dict:
        """Human-only release, mirroring the kill-switch principle."""
        state.set_kv(HALT_KEY, {"engaged": False})
        state.audit(actor, "recon.release", {})
        log.info("recon_released", extra={"actor": actor})
        return {"engaged": False}

    def status(self) -> dict:
        return {
            "halted": entries_halted(),
            "halt": state.get_kv(HALT_KEY),
            "last": state.get_kv(LAST_KEY),
        }
