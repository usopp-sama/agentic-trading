"""Execution Service (Phase 2 core; extended with the autonomy switch in Phase 7).

Owns the paper broker and portfolio accounting, subscribes to decisions, and
records a periodic equity snapshot. In v1 everything routes to paper. The
four-state autonomy switch and the real broker adapter are layered on in
Phase 7 without changing this service's external surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Approval, Decision, Fill, Order, PnlDaily
from ats.core import state
from ats.services.execution.autonomy import resolve_route
from ats.services.execution.kite_adapter import KiteAdapter
from ats.services.execution.notify import notify
from ats.services.execution.paper_broker import PaperBroker
from ats.services.execution.portfolio import snapshot
from ats.services.market_data.store import load_history

log = get_logger("ats.execution")


@dataclass
class Draft:
    """A staged order awaiting commit (two-stage commit)."""

    decision_id: int | None
    symbol: str
    side: str
    qty: int
    est_price: float
    use_real: bool

    @property
    def est_value(self) -> float:
        return round(self.qty * self.est_price, 2)


class ExecutionService:
    name = "execution"

    def __init__(self) -> None:
        self.account = "paper"
        self.broker = PaperBroker(account=self.account)
        self.kite = KiteAdapter()
        self._bus: EventBus | None = None
        self._md = None
        self._peak_equity = 0.0
        self._pending: dict[int, Draft] = {}

    @property
    def _peak_key(self) -> str:
        return f"risk:peak_equity:{self.account}"

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._md = ctx.orchestrator.get("market_data")
        self.broker.set_price_fn(self.price_of)
        # Recover peak equity so the drawdown-based daily-loss kill switch is
        # not silently reset to 0 by a mid-month restart.
        self._peak_equity = float(state.get_kv(self._peak_key, {"peak": 0.0}).get("peak", 0.0))
        if self._peak_equity > 0:
            log.info("peak_equity_restored", extra={"peak": self._peak_equity})
        ctx.bus.subscribe(Topic.DECISION, self._on_decision)

        from ats.core.config import get_settings

        settings = get_settings()
        ctx.scheduler.add_job(
            self.record_equity, "interval",
            seconds=max(60, settings.market_scan_interval_s),
            id="equity_snapshot", max_instances=1, coalesce=True,
        )

        # Daily digest pushed shortly after the NSE close (IST), so an
        # unattended run reports each day's outcome over the notify channel.
        from ats.services.market_data.calendar import IST

        ctx.scheduler.add_job(
            self.push_daily_digest, "cron",
            hour=settings.digest_hour, minute=settings.digest_minute, timezone=IST,
            id="daily_digest", max_instances=1, coalesce=True,
        )

    def _feed_degraded(self) -> bool:
        from ats.core.config import get_settings

        if not get_settings().feed_halt_entries_on_degrade:
            return False
        healthy_fn = getattr(self._md, "feed_healthy", None)
        return bool(healthy_fn is not None and not healthy_fn())

    # --- price oracle ------------------------------------------------------
    def price_of(self, symbol: str) -> float | None:
        if self._md is not None:
            px = self._md.latest_price(symbol)
            if px is not None:
                return px
        hist = load_history(symbol, limit=1)
        if not hist.empty:
            return float(hist["close"].iloc[-1])
        return None

    # --- decision handling -------------------------------------------------
    async def _on_decision(self, evt) -> None:
        await self.execute_decision(evt.payload)

    async def execute_decision(self, decision: dict) -> dict:
        action = decision.get("action", "HOLD").upper()
        qty = int(decision.get("target_qty", decision.get("qty", 0)))
        symbol = decision.get("symbol")
        if action == "HOLD" or qty <= 0 or not symbol:
            return {"status": "SKIPPED"}

        route = resolve_route(state.get_mode(), state.is_killed(), state.real_money_active())
        if not route.allowed:
            log.warning("execution_blocked", extra={"symbol": symbol, "reason": route.reason})
            return {"status": "BLOCKED", "reason": route.reason}

        side = "BUY" if action == "BUY" else "SELL"

        # Feed-integrity gate: never OPEN new exposure on a degraded (mostly
        # synthetic) live feed. Exits (SELL) are always allowed so positions can
        # still be managed when data is poor.
        if side == "BUY" and self._feed_degraded():
            log.warning("entry_blocked_feed_degraded", extra={"symbol": symbol})
            return {"status": "BLOCKED", "reason": "feed_degraded"}
        price = self.price_of(symbol) or 0.0
        draft = Draft(
            decision_id=decision.get("decision_id"),
            symbol=symbol, side=side, qty=qty, est_price=price, use_real=route.use_real,
        )

        if route.needs_approval:
            return self._request_approval(draft)
        return await self._commit(draft)

    # --- two-stage commit --------------------------------------------------
    def _request_approval(self, draft: Draft) -> dict:
        if draft.decision_id is not None:
            self._pending[draft.decision_id] = draft
            with session_scope() as s:
                s.add(Approval(decision_id=draft.decision_id, channel="dashboard", result="pending"))
        notify(
            f"APPROVAL NEEDED: {draft.side} {draft.qty} {draft.symbol} "
            f"~Rs{draft.est_value} ({'REAL' if draft.use_real else 'paper'}). "
            f"Decision #{draft.decision_id}."
        )
        if self._bus is not None:
            import asyncio

            asyncio.create_task(
                self._bus.publish(
                    Topic.APPROVAL_REQUEST,
                    {"decision_id": draft.decision_id, "symbol": draft.symbol,
                     "side": draft.side, "qty": draft.qty, "est_value": draft.est_value},
                )
            )
        return {"status": "PENDING_APPROVAL", "decision_id": draft.decision_id}

    async def _commit(self, draft: Draft) -> dict:
        # Real-broker routing is reachable only when the gate is open; in v1 it
        # is always paper. The Kite adapter itself also refuses without the gate.
        broker = self.kite if draft.use_real else self.broker
        result = broker.submit(
            draft.symbol, draft.side, draft.qty, decision_id=draft.decision_id
        )
        if result.get("status") == "FILLED":
            if draft.decision_id is not None:
                self._mark_decision(draft.decision_id, "filled")
            if self._bus is not None:
                await self._bus.publish(Topic.FILL, {**result, "decision_id": draft.decision_id})
        return result

    # --- approval workflow -------------------------------------------------
    def list_pending_approvals(self) -> list[dict]:
        with session_scope() as s:
            rows = s.execute(
                select(Approval).where(Approval.result == "pending")
            ).scalars().all()
            return [
                {"id": a.id, "decision_id": a.decision_id, "requested": a.requested_ts.isoformat()}
                for a in rows
            ]

    async def approve_decision(self, decision_id: int, actor: str = "human") -> dict:
        draft = self._pending.get(decision_id) or self._rebuild_draft(decision_id)
        if draft is None:
            return {"status": "NOT_FOUND"}
        self._resolve_approval(decision_id, "approved", actor)
        self._pending.pop(decision_id, None)
        state.audit(actor, "approval.approve", {"decision_id": decision_id})
        return await self._commit(draft)

    def reject_decision(self, decision_id: int, actor: str = "human") -> dict:
        self._resolve_approval(decision_id, "rejected", actor)
        self._pending.pop(decision_id, None)
        self._mark_decision(decision_id, "rejected")
        state.audit(actor, "approval.reject", {"decision_id": decision_id})
        return {"status": "REJECTED", "decision_id": decision_id}

    def _rebuild_draft(self, decision_id: int) -> Draft | None:
        with session_scope() as s:
            d = s.get(Decision, decision_id)
            if d is None or d.action == "HOLD":
                return None
            price = self.price_of(d.symbol) or 0.0
            return Draft(decision_id, d.symbol, d.action, d.target_qty, price,
                         use_real=state.real_money_active())

    def _resolve_approval(self, decision_id: int, result: str, actor: str) -> None:
        with session_scope() as s:
            row = s.execute(
                select(Approval).where(Approval.decision_id == decision_id, Approval.result == "pending")
            ).scalar_one_or_none()
            if row:
                row.result = result
                row.actor = actor
                row.responded_ts = datetime.now(timezone.utc)

    @staticmethod
    def _mark_decision(decision_id: int, status: str) -> None:
        with session_scope() as s:
            d = s.get(Decision, decision_id)
            if d:
                d.status = status

    async def submit_market_order(self, symbol: str, side: str, qty: int) -> dict:
        """Direct order entry (used by tests/harness); always paper."""
        result = self.broker.submit(symbol, side, qty)
        if result.get("status") == "FILLED" and self._bus is not None:
            await self._bus.publish(Topic.FILL, result)
        return result

    # --- portfolio + pnl ---------------------------------------------------
    def get_snapshot(self) -> dict:
        return snapshot(self.account, self.price_of)

    def record_equity(self) -> dict:
        snap = self.get_snapshot()
        equity = snap["equity"]
        prev_peak = self._peak_equity
        self._peak_equity = max(self._peak_equity, equity)
        if self._peak_equity > prev_peak:
            # Persist new high-water marks so drawdown survives a restart.
            state.set_kv(self._peak_key, {"peak": self._peak_equity})
        drawdown = (equity / self._peak_equity - 1.0) if self._peak_equity > 0 else 0.0
        net = snap["realized_pnl"] + snap["unrealized_pnl"]
        today = date.today()
        with session_scope() as s:
            # Cumulative fees paid by this account (for the gross/net split).
            fees = float(
                s.execute(
                    select(func.coalesce(func.sum(Fill.fees), 0.0))
                    .join(Order, Fill.order_id == Order.id)
                    .where(Order.account == self.account)
                ).scalar_one()
                or 0.0
            )
            row = s.execute(
                select(PnlDaily).where(
                    PnlDaily.account == self.account, PnlDaily.day == today
                )
            ).scalar_one_or_none()
            if row is None:
                row = PnlDaily(account=self.account, day=today)
                s.add(row)
            row.equity = equity
            row.net = net
            # Complete the daily accounting: gross (pre-fee) and fees to date.
            row.fees = round(fees, 2)
            row.gross = round(net + fees, 2)
            row.drawdown = round(drawdown, 4)
        return {"equity": equity, "drawdown": round(drawdown, 4)}

    def push_daily_digest(self) -> dict:
        """Compose and send an end-of-day summary over the notify channel.

        Skipped on non-trading days. Refreshes the equity row first so the
        numbers reflect the close.
        """
        from ats.services.market_data.calendar import is_trading_day

        today = date.today()
        if not is_trading_day(today):
            return {"skipped": "not_trading_day"}
        try:
            self.record_equity()
        except Exception as exc:  # noqa: BLE001 - digest must not raise in cron
            log.warning("digest_record_equity_failed", extra={"error": str(exc)})
        snap = self.get_snapshot()
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        with session_scope() as s:
            row = s.execute(
                select(PnlDaily).where(
                    PnlDaily.account == self.account, PnlDaily.day == today
                )
            ).scalar_one_or_none()
            fills_24h = int(
                s.execute(
                    select(func.count(Fill.id))
                    .join(Order, Fill.order_id == Order.id)
                    .where(Order.account == self.account, Fill.ts >= cutoff)
                ).scalar_one()
                or 0
            )
        net = float(row.net) if row else 0.0
        dd = float(row.drawdown) if row else 0.0
        cur = "Rs"
        msg = (
            f"Daily digest {today.isoformat()}: equity {cur}{snap['equity']:,.0f} | "
            f"net P&L {cur}{net:+,.0f} | drawdown {dd * 100:.1f}% | "
            f"{fills_24h} fills (24h) | {len(snap['positions'])} open positions."
        )
        notify(msg)
        log.info("daily_digest", extra={"net": round(net, 2), "fills_24h": fills_24h})
        return {"digest": msg, "net": net, "fills_24h": fills_24h}
