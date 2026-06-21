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
from ats.services.agents.console import ExpertConsole
from ats.services.agents.directives import get_directive_store
from ats.services.agents.knowledge_base import get_knowledge_base
from ats.services.agents.llm_client import select_llm_clients
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
        self._console: ExpertConsole | None = None
        self._llm_status: dict = {"provider": "mock", "real": False}
        # Debounce macro re-evaluation driven by incoming news.
        self._last_macro_news: float = 0.0
        self._macro_news_min_gap_s: float = 90.0

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        providers = Providers(
            market_data=ctx.orchestrator.get("market_data"),
            strategies=ctx.orchestrator.get("strategies"),
            nlp=ctx.orchestrator.get("nlp"),
            knowledge=ctx.orchestrator.get("knowledge"),
            fundamentals=ctx.orchestrator.get("fundamentals"),
        )
        # Build the SME + CIO LLM clients and verify a real provider actually
        # answers; if not, downgrade to the deterministic mock for this session
        # (prevents a 60s-per-call timeout when Ollama/API is misconfigured).
        sme_llm, cio_llm, self._llm_status = select_llm_clients()
        self._runtime = SmeRuntime(providers, llm_client=sme_llm)
        self._personas = self._load_personas()
        self._by_id = {p["id"]: p for p in self._personas}
        self._symbol_personas = [p for p in self._personas if p["scope"] == "symbol"]
        self._macro_personas = [p for p in self._personas if p["scope"] == "market"]

        # Domain knowledge base for grounding (built-in primers + user docs)
        # and self-evolving expert directives (context only).
        get_knowledge_base().ingest_all(providers.knowledge)
        get_directive_store().load_all()

        # Interactive expert console (tiered routing: stronger model for CIO).
        self._console = ExpertConsole(providers, self._by_id, sme_llm, cio_llm)

        ctx.bus.subscribe(Topic.VOLUME_SPIKE, self._on_spike)
        ctx.bus.subscribe(Topic.SENTIMENT, self._on_sentiment)

        from ats.core.config import get_settings

        ctx.scheduler.add_job(
            self._scheduled_macro_sweep, "interval",
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
        # Portfolio/watchlist impact: the named tickers get a fresh symbol-scope
        # SME read.
        for symbol in evt.payload.get("tickers", []):
            if not symbol.startswith("^"):
                await self.run_symbol(symbol)
        # World-market impact: any news (including ticker-less macro/world news)
        # nudges the macro (Family B) experts to re-read the latest headlines.
        # Debounced so a burst of items triggers a single re-evaluation.
        await self._maybe_refresh_macro_from_news()

    async def _maybe_refresh_macro_from_news(self) -> None:
        import time

        now = time.monotonic()
        if now - self._last_macro_news < self._macro_news_min_gap_s:
            return
        self._last_macro_news = now
        try:
            await self.refresh_macro()
        except Exception as exc:  # noqa: BLE001 - macro refresh is best-effort
            log.warning("macro_refresh_on_news_failed", extra={"error": str(exc)})

    async def _scheduled_macro_sweep(self) -> None:
        """Periodic macro refresh, gated to the NSE session. News arriving at
        any hour still triggers a macro re-read via ``_maybe_refresh_macro_from_news``;
        this only skips the *redundant* clock-driven sweep when the market is shut."""
        from ats.core.config import get_settings
        from ats.services.market_data.calendar import is_polling_window

        if get_settings().respect_market_hours and not is_polling_window():
            return
        await self.refresh_macro()

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

    # --- debate (multi-expert) --------------------------------------------
    async def debate(self, symbol: str, rounds: int | None = None) -> dict:
        """Run a structured debate: every symbol-scope expert opines, then
        (with a real LLM) reconsiders given peers' views, and finally the CIO
        synthesizes a proposal. With the mock client the rebuttal rounds are
        skipped (the heuristic has no new information to react to)."""
        if self._runtime is None:
            return {"symbol": symbol, "error": "runtime unavailable"}
        from ats.core.config import get_settings

        symbol = symbol.strip().upper()
        rounds = rounds if rounds is not None else get_settings().debate_rounds
        personas = list(self._symbol_personas)
        is_real = bool(getattr(self._runtime.llm, "is_real", False))

        opinions: dict[str, object] = {}
        for p in personas:
            try:
                opinions[p["id"]] = self._runtime.opine(p, symbol)
            except Exception as exc:  # noqa: BLE001
                log.warning("debate_opine_failed", extra={"sme": p["id"], "error": str(exc)})

        transcript = [{"round": 0, "opinions": self._debate_round(personas, opinions)}]

        effective_rounds = rounds if is_real else 0
        for r in range(1, effective_rounds + 1):
            peers = self._peer_summaries(opinions)
            updated: dict[str, object] = {}
            for p in personas:
                others = [op for sid, op in peers.items() if sid != p["id"]]
                try:
                    updated[p["id"]] = self._runtime.opine(p, symbol, {"peer_opinions": others})
                except Exception:  # noqa: BLE001
                    updated[p["id"]] = opinions.get(p["id"])
            opinions = {k: v for k, v in updated.items() if v is not None}
            transcript.append({"round": r, "opinions": self._debate_round(personas, opinions)})

        weights = {
            p["id"]: self._effective_weight(p)
            for p in personas
            if p["family"] != "RISK" and p["id"] in opinions
        }
        proposal = self._cio.aggregate(
            symbol, [opinions[k] for k in weights], weights, self._macro_tilt
        )
        if self._bus is not None:
            await self._bus.publish(
                Topic.OPINION, {"kind": "debate", "symbol": symbol, "action": proposal.action}
            )
        return {
            "symbol": symbol,
            "rounds": effective_rounds,
            "is_real": is_real,
            "macro_tilt": round(self._macro_tilt, 3),
            "transcript": transcript,
            "proposal": proposal.model_dump(mode="json"),
        }

    def _debate_round(self, personas: list[dict], opinions: dict) -> list[dict]:
        by_id = {p["id"]: p for p in personas}
        out = []
        for sid, op in opinions.items():
            p = by_id.get(sid, {})
            out.append(
                {
                    "sme": sid,
                    "name": p.get("name", sid),
                    "family": p.get("family"),
                    "stance": op.stance.value,
                    "conviction": round(op.conviction, 3),
                    "rationale": op.rationale,
                    "key_risks": op.key_risks,
                }
            )
        return out

    @staticmethod
    def _peer_summaries(opinions: dict) -> dict[str, dict]:
        return {
            sid: {
                "sme": sid,
                "stance": op.stance.value,
                "conviction": round(op.conviction, 3),
                "rationale": op.rationale,
            }
            for sid, op in opinions.items()
        }

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

    def console(self) -> ExpertConsole | None:
        return self._console

    def llm_status(self) -> dict:
        """Startup self-check result: is real reasoning actually live?"""
        return dict(self._llm_status)

    @property
    def macro_tilt(self) -> float:
        return self._macro_tilt
