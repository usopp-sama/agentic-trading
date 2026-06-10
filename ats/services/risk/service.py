"""Risk Service.

The mandatory clamp/veto layer between CIO proposals and execution. It sizes
the position (allocator), enforces immutable guardrails, rate-limits order
flow, engages the kill switch on a daily-loss breach, records an auditable
Decision, and only then publishes a DECISION for execution. Nothing reaches a
broker without passing through here.
"""

from __future__ import annotations

import time
from collections import deque

from sqlalchemy import select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Decision, Instrument
from ats.services.risk.allocator import desired_target_qty
from ats.services.risk.guardrails import GuardrailInput, apply_guardrails

log = get_logger("ats.risk")


class RiskService:
    name = "risk"

    def __init__(self) -> None:
        self._bus: EventBus | None = None
        self._md = None
        self._execution = None
        self._sectors: dict[str, str] = {}
        self._order_times: deque[float] = deque(maxlen=200)
        self._orch = None

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._md = ctx.orchestrator.get("market_data")
        self._execution = ctx.orchestrator.get("execution")
        self._orch = ctx.orchestrator
        with session_scope() as s:
            self._sectors = {
                r.symbol: r.sector for r in s.execute(select(Instrument)).scalars().all()
            }
        ctx.bus.subscribe(Topic.PROPOSAL, self._on_proposal)

    async def _on_proposal(self, evt) -> None:
        await self.evaluate_proposal(evt.payload)

    async def evaluate_proposal(self, proposal: dict) -> dict:
        symbol = proposal.get("symbol")
        if not symbol or self._execution is None:
            return {"status": "skipped"}

        settings = get_settings()
        price = self._price(symbol)
        if price is None:
            return {"status": "no_price"}

        snap = self._execution.get_snapshot()
        equity = snap["equity"]
        positions = {p["symbol"]: p for p in snap["positions"]}
        current_qty = positions.get(symbol, {}).get("qty", 0)
        sector = self._sectors.get(symbol, "Unknown")

        sector_value_excl = sum(
            p["market_value"] for sym, p in positions.items()
            if sym != symbol and self._sectors.get(sym) == sector
        )
        gross_value_excl = snap["holdings_value"] - positions.get(symbol, {}).get("market_value", 0.0)
        drawdown = self._execution.record_equity().get("drawdown", 0.0)

        desired = desired_target_qty(
            target_weight=proposal.get("target_weight", 0.0),
            conviction=proposal.get("conviction", 0.0),
            equity=equity,
            price=price,
            max_position_pct=settings.max_position_pct,
        )

        # Rate limit: reject if too many orders in the last 60s.
        if self._rate_limited(settings.max_orders_per_min):
            self._record_decision(proposal, "HOLD", 0, ["rate_limit"], status="blocked")
            return {"status": "rate_limited"}

        result = apply_guardrails(
            GuardrailInput(
                symbol=symbol, sector=sector, price=price,
                desired_target_qty=desired, current_qty=current_qty, equity=equity,
                sector_value_excl_symbol=sector_value_excl,
                gross_value_excl_symbol=gross_value_excl,
                drawdown=drawdown,
                max_position_pct=settings.max_position_pct,
                max_sector_pct=settings.max_sector_pct,
                max_gross_pct=settings.max_gross_exposure_pct,
                daily_loss_limit_pct=settings.daily_loss_limit_pct,
                max_trade_value=settings.max_trade_value,
            )
        )

        if result.kill and not state.is_killed():
            state.engage_kill_switch(actor="risk_manager", reason="daily_loss_limit breached")

        # Adaptive rulebook: an additional, conservative-only clamp/veto layer.
        rule_applied = self._apply_adaptive_rules(symbol, result)
        result.applied.extend(rule_applied)

        if result.side == "HOLD" or result.delta_qty == 0:
            self._record_decision(proposal, "HOLD", 0, result.applied, status="blocked")
            return {"status": "blocked", "applied": result.applied}

        decision_id = self._record_decision(
            proposal, result.side, abs(result.delta_qty), result.applied, status="approved"
        )
        self._order_times.append(time.monotonic())
        if self._bus is not None:
            await self._bus.publish(
                Topic.DECISION,
                {
                    "symbol": symbol,
                    "action": result.side,
                    "qty": abs(result.delta_qty),
                    "target_qty": abs(result.delta_qty),
                    "decision_id": decision_id,
                    "mode": state.get_mode(),
                },
            )
        return {"status": "approved", "side": result.side, "qty": abs(result.delta_qty), "applied": result.applied}

    def _apply_adaptive_rules(self, symbol: str, result) -> list[str]:
        rules = self._orch.get("rules") if self._orch else None
        if rules is None or result.delta_qty <= 0:  # only gate new buys
            return []
        from ats.services.agents.tools import Providers, get_technical, get_volume

        p = Providers(market_data=self._md)
        ctx = {**get_technical(p, symbol), **get_volume(p, symbol)}
        effect = rules.evaluate(ctx)
        if effect["block"]:
            result.side = "HOLD"
            result.delta_qty = 0
            return [f"rule:{r}" for r in effect["applied"]]
        if effect["scale"] < 1.0:
            result.delta_qty = int(result.delta_qty * effect["scale"])
            if result.delta_qty == 0:
                result.side = "HOLD"
        return [f"rule:{r}" for r in effect["applied"]]

    # --- helpers -----------------------------------------------------------
    def _price(self, symbol: str) -> float | None:
        if self._md is not None:
            px = self._md.latest_price(symbol)
            if px is not None:
                return px
        return self._execution.price_of(symbol) if self._execution else None

    def _rate_limited(self, max_per_min: int) -> bool:
        now = time.monotonic()
        while self._order_times and now - self._order_times[0] > 60.0:
            self._order_times.popleft()
        return len(self._order_times) >= max_per_min

    def _record_decision(self, proposal: dict, action: str, qty: int, applied: list[str], status: str) -> int:
        with session_scope() as s:
            d = Decision(
                symbol=proposal.get("symbol"),
                action=action,
                target_qty=qty,
                mode=state.get_mode(),
                rationale=proposal.get("rationale", ""),
                contributors=proposal.get("contributors", {}),
                rules_applied=applied,
                status=status,
            )
            s.add(d)
            s.flush()
            return d.id
