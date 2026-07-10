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

import asyncio

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.telemetry import instrument
from ats.core.models import SmeTrackRecord
from ats.core.schemas import Opinion, ProposedPosition
from ats.services.agents.cio import CIO
from ats.services.agents.console import ExpertConsole
from ats.services.agents.directives import get_directive_store
from ats.services.agents.gating import SymbolCooldown, eval_window_open, rank_symbols
from ats.services.agents.knowledge_base import get_knowledge_base
from ats.services.agents.news_routing import classify_themes, route_macro_personas
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
        self._market_data = None  # set in start(); used for the universe filter
        self._execution = None    # set in start(); used to scope news to holdings
        # Debounce macro re-evaluation driven by incoming news.
        self._last_macro_news: float = 0.0
        self._macro_news_min_gap_s: float = 90.0
        # Per-symbol cooldown so a burst of news on one name costs a single
        # autonomous SME evaluation rather than one full roster pass per item.
        self._cooldown = SymbolCooldown()

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        providers = Providers(
            market_data=ctx.orchestrator.get("market_data"),
            strategies=ctx.orchestrator.get("strategies"),
            nlp=ctx.orchestrator.get("nlp"),
            knowledge=ctx.orchestrator.get("knowledge"),
            fundamentals=ctx.orchestrator.get("fundamentals"),
        )
        self._market_data = providers.market_data
        self._execution = ctx.orchestrator.get("execution")
        # Build the SME + CIO LLM clients and probe whether a real provider
        # answers. A failed probe no longer pins the session to the mock: the
        # clients are resilient and auto-recover once the provider is reachable
        # (e.g. after a transient 429). llm_status() reports the live state.
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
    # Cost governance lives here: the autonomous triggers below are the only
    # paths that can spend Gemini tokens unattended, so they enforce the clock
    # window, universe filter, per-symbol cooldown, and fan-out cap. The manual
    # ``run_symbol``/console/brief paths stay unthrottled on purpose.

    def _universe(self) -> list[str] | None:
        if self._market_data is None:
            return None
        try:
            return self._market_data.watchlist()
        except Exception:  # noqa: BLE001 - never let the filter break a trigger
            return None

    def _held_symbols(self) -> set[str]:
        """Symbols we currently hold (qty > 0) in the paper book, upper-cased."""
        if self._execution is None:
            return set()
        try:
            snap = self._execution.get_snapshot()
        except Exception:  # noqa: BLE001 - never let accounting break a trigger
            return set()
        return {
            str(p.get("symbol", "")).upper()
            for p in snap.get("positions", [])
            if p.get("qty", 0)
        }

    async def _evaluate(self, symbols: list[str], force: set[str] | None = None) -> None:
        """Run the symbol-scope SMEs for each gated symbol, marking cooldowns.

        ``force`` is the set of held names mentioned in the trigger: we always
        re-read news on what we own (bypassing the per-symbol cooldown) so the
        book reacts to fresh information, and they run first.
        """
        from ats.core.config import get_settings

        cooldown = get_settings().llm_symbol_cooldown_s
        force = {s.upper() for s in (force or set())}
        # Held names first (forced), then the gated set; de-duped, order-preserving.
        ordered = list(dict.fromkeys(list(force) + list(symbols)))
        for symbol in ordered:
            forced = symbol.upper() in force
            if not forced and not self._cooldown.ready(symbol, cooldown):
                log.debug("sme_skip_cooldown", extra={"symbol": symbol})
                continue
            self._cooldown.mark(symbol)
            await self.run_symbol(symbol)

    async def _on_spike(self, evt) -> None:
        if not eval_window_open():
            return
        from ats.core.config import get_settings

        s = get_settings()
        # WS-3: with the SME trade path off, spikes spend no LLM tokens — the
        # spike is already persisted for the slow loop's weekly research read.
        if not s.sme_trade_path:
            return
        symbol = evt.payload.get("symbol")
        gated = rank_symbols(
            [symbol] if symbol else [],
            universe=self._universe(),
            universe_only=s.llm_eval_universe_only,
            cap=max(1, s.llm_max_symbols_per_event),
        )
        await self._evaluate(gated)

    async def _on_sentiment(self, evt) -> None:
        # No autonomous spend outside the session: the news has already been
        # fetched and scored locally and persisted, so the SMEs pick it up when
        # the market re-opens. Nothing is lost, we just defer the reasoning.
        if not eval_window_open():
            return
        from ats.core.config import get_settings

        s = get_settings()
        # WS-3: with the SME trade path off, the news->SME fan-out (the
        # expensive path) is severed. The item is already scored + archived
        # (NLP), and the severity flag still protects the fast loop.
        if not s.sme_trade_path:
            return
        tickers = evt.payload.get("tickers", [])
        # Portfolio/watchlist impact: a capped, de-duped, universe-filtered set
        # of the named tickers get a fresh symbol-scope SME read.
        gated = rank_symbols(
            tickers,
            universe=self._universe(),
            universe_only=s.llm_eval_universe_only,
            cap=max(1, s.llm_max_symbols_per_event),
        )
        # Holdings-scoped monitoring: any name we currently OWN that this news
        # mentions is always evaluated -- even if the universe filter or fan-out
        # cap would have dropped it -- and bypasses the cooldown. We want to act
        # on fresh information about our own book promptly and deliberately.
        held = self._held_symbols()
        forced = {t.strip().upper() for t in tickers if t and t.strip().upper() in held}
        await self._evaluate(gated, force=forced)
        # World-market impact: theme-route the headline so only the relevant
        # macro (Family B) experts re-read, instead of the whole roster.
        # Debounced so a burst of items triggers a single re-evaluation.
        themes = classify_themes(evt.payload.get("title", ""))
        await self._maybe_refresh_macro_from_news(themes)

    async def _maybe_refresh_macro_from_news(self, themes: set[str] | None = None) -> None:
        import time

        if not eval_window_open():
            return
        now = time.monotonic()
        if now - self._last_macro_news < self._macro_news_min_gap_s:
            return
        self._last_macro_news = now
        # Route to the experts whose themes the headline touches (+ the always-on
        # core). An unclassifiable headline runs only the core, not all 16.
        routed = route_macro_personas(themes, self._macro_personas)
        try:
            await self.refresh_macro(routed)
        except Exception as exc:  # noqa: BLE001 - macro refresh is best-effort
            log.warning("macro_refresh_on_news_failed", extra={"error": str(exc)})

    @instrument("agents", "macro_sweep")
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
    async def refresh_macro(self, personas: list[dict] | None = None) -> float:
        """Re-read the macro view. ``personas`` lets a news trigger run only the
        theme-relevant subset; the periodic sweep passes ``None`` for a full read."""
        if self._runtime is None:
            return 0.0
        pool = personas if personas is not None else self._macro_personas
        num = den = 0.0
        for persona in pool:
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
        from ats.core.config import get_settings

        # WS-3: with the SME trade path off, the CIO's view is analysis only —
        # it never becomes an order. Manual console runs still get the full
        # opinions + synthesis to read.
        if (
            self._bus is not None
            and proposal.action != "HOLD"
            and get_settings().sme_trade_path
        ):
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
                opinions[p["id"]] = await asyncio.to_thread(self._runtime.opine, p, symbol)
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
                    updated[p["id"]] = await asyncio.to_thread(
                        self._runtime.opine, p, symbol, {"peer_opinions": others}
                    )
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
        """Live LLM health: reflects auto-recovery, not just the startup probe.

        Reads the resilient client's current state so ``/api/health`` shows the
        provider coming back online after a transient outage without a restart.
        Falls back to the startup snapshot if the client predates this contract.
        """
        client = getattr(self._runtime, "llm", None)
        if client is not None and hasattr(client, "status"):
            try:
                return client.status()
            except Exception:  # noqa: BLE001 - status must never break health
                pass
        return dict(self._llm_status)

    @property
    def macro_tilt(self) -> float:
        return self._macro_tilt
