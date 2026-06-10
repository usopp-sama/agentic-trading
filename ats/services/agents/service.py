"""Agent Service.

Owns the SME runtime + the full persona roster (4 families) + the CIO. On
triggers (volume spike, fresh sentiment) or a periodic sweep it runs the
symbol-scope SMEs, refreshes the market-level (Family B) view on a slower
cadence, then asks the CIO to synthesize a ranked proposal which it publishes
for the Risk Manager (Phase 6).

Effective vote weight = persona base weight x learned vote weight (Phase 8).
Shadow SMEs have weight 0: visible for transparency, but they cannot move money
until promoted. RISK-family personas never vote on direction.
"""

from __future__ import annotations

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import SmeTrackRecord
from ats.core.schemas import Opinion, ProposedPosition
from ats.services.agents.cio import CIO
from ats.services.agents.registry import families, load_personas
from ats.services.agents.runtime import SmeRuntime
from ats.services.agents.tools import Providers

log = get_logger("ats.agents")

_MARKET = "MARKET"


class AgentService:
    name = "agents"

    def __init__(self) -> None:
        self._bus: EventBus | None = None
        self._runtime: SmeRuntime | None = None
        self._cio = CIO()
        self._personas: list[dict] = []
        self._by_id: dict[str, dict] = {}
        self._symbol_personas: list[dict] = []
        self._macro_personas: list[dict] = []
        self._macro_tilt: float = 0.0

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        providers = Providers(
            market_data=ctx.orchestrator.get("market_data"),
            strategies=ctx.orchestrator.get("strategies"),
            nlp=ctx.orchestrator.get("nlp"),
            knowledge=ctx.orchestrator.get("knowledge"),
        )
        self._runtime = SmeRuntime(providers)
        self._personas = self._load_personas()
        self._by_id = {p["id"]: p for p in self._personas}
        self._symbol_personas = [p for p in self._personas if p["scope"] == "symbol"]
        self._macro_personas = [p for p in self._personas if p["scope"] == "market"]

        ctx.bus.subscribe(Topic.VOLUME_SPIKE, self._on_spike)
        ctx.bus.subscribe(Topic.SENTIMENT, self._on_sentiment)

        from ats.core.config import get_settings

        ctx.scheduler.add_job(
            self.refresh_macro, "interval",
            seconds=max(300, get_settings().agent_cycle_interval_s * 3),
            id="agent_macro", max_instances=1, coalesce=True,
        )
        log.info("agents_ready", extra={"personas": len(self._personas), "families": families(self._personas)})

    def _load_personas(self) -> list[dict]:
        return load_personas()

    # --- triggers ----------------------------------------------------------
    async def _on_spike(self, evt) -> None:
        symbol = evt.payload.get("symbol")
        if symbol and not symbol.startswith("^"):
            await self.run_symbol(symbol)

    async def _on_sentiment(self, evt) -> None:
        for symbol in evt.payload.get("tickers", []):
            if not symbol.startswith("^"):
                await self.run_symbol(symbol)

    # --- macro (Family B) --------------------------------------------------
    async def refresh_macro(self) -> float:
        if self._runtime is None:
            return 0.0
        num = den = 0.0
        for persona in self._macro_personas:
            op = await self._runtime.run(persona, _MARKET, self._bus)
            w = self._effective_weight(persona)
            num += w * (op.stance.direction / 2.0) * op.conviction
            den += w
        self._macro_tilt = (num / den) if den > 0 else 0.0
        return self._macro_tilt

    # --- per-symbol pipeline ----------------------------------------------
    async def run_symbol(self, symbol: str) -> tuple[list[Opinion], ProposedPosition]:
        if self._runtime is None:
            return [], ProposedPosition(symbol=symbol)
        opinions: list[Opinion] = []
        weights: dict[str, float] = {}
        for persona in self._symbol_personas:
            try:
                op = await self._runtime.run(persona, symbol, self._bus)
            except Exception as exc:  # noqa: BLE001
                log.warning("opinion_failed", extra={"sme": persona["id"], "symbol": symbol, "error": str(exc)})
                continue
            opinions.append(op)
            if persona["family"] != "RISK":
                weights[persona["id"]] = self._effective_weight(persona)

        proposal = self._cio.aggregate(symbol, opinions, weights, self._macro_tilt)
        if self._bus is not None and proposal.action != "HOLD":
            await self._bus.publish(Topic.PROPOSAL, proposal.model_dump(mode="json"))
        return opinions, proposal

    # --- weights -----------------------------------------------------------
    def _effective_weight(self, persona: dict) -> float:
        base = float(persona.get("weight", 0.0))
        with session_scope() as s:
            tr = s.get(SmeTrackRecord, persona["id"])
            vote = float(tr.vote_weight) if tr else 1.0
            promoted = float(tr.promoted_weight) if tr else 0.0
        # A learned promotion can lift a shadow SME (base 0); vote weight scales
        # influence by track record. Effective weight is never below 0.
        effective_base = max(base, promoted)
        return effective_base * vote

    # --- introspection -----------------------------------------------------
    def personas(self) -> list[dict]:
        return list(self._personas)

    @property
    def macro_tilt(self) -> float:
        return self._macro_tilt
