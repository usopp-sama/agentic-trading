"""SME agent runtime.

The per-SME loop:
    trigger -> deterministic context assembly -> LLM opinion
            -> schema validation -> cache/debounce -> persist -> publish.

Caching keys on the *grounded signals*, so an SME does not re-opine (or spend
tokens) until its evidence actually changes. Scraped/news text only ever enters
the model as delimited DATA (handled in the LLM client), never as instructions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import SmeOpinion
from ats.core.schemas import Horizon, Opinion, Stance
from ats.services.agents.context import ContextAssembler
from ats.services.agents.llm_client import LLMClient, build_llm_client
from ats.services.agents.tools import Providers

log = get_logger("ats.agent_runtime")

_CACHE_TTL_S = 300.0


class SmeRuntime:
    def __init__(self, providers: Providers, llm_client: LLMClient | None = None) -> None:
        self.assembler = ContextAssembler(providers)
        self.llm = llm_client or build_llm_client("sme")
        self._cache: dict[str, tuple[str, Opinion, float]] = {}

    async def run(self, persona: dict, symbol: str, bus: EventBus | None = None) -> Opinion:
        context = self.assembler.assemble(persona, symbol)
        sig_hash = _signals_hash(persona["id"], symbol, context["signals"])
        cache_key = f"{persona['id']}:{symbol}"
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached and cached[0] == sig_hash and (now - cached[2]) < _CACHE_TTL_S:
            return cached[1]

        # The LLM client does blocking network I/O (and retry/backoff sleeps);
        # run it off the event loop so the web server / dashboard stay responsive
        # during SME bursts and provider throttling.
        raw = await asyncio.to_thread(self.llm.generate_opinion, persona, context)
        opinion = self._validate(persona, symbol, raw, context)
        self._persist(opinion)
        self._cache[cache_key] = (sig_hash, opinion, now)
        if bus is not None:
            await bus.publish(Topic.OPINION, opinion.model_dump(mode="json"))
        return opinion

    def opine(self, persona: dict, symbol: str, extra_context: dict | None = None) -> Opinion:
        """One grounded opinion with no caching/persistence/publishing.

        Used by the debate orchestrator to re-poll an expert with peer context
        merged in, without touching the live cache or event stream.
        """
        context = self.assembler.assemble(persona, symbol)
        if extra_context:
            context = {**context, **extra_context}
        raw = self.llm.generate_opinion(persona, context)
        return self._validate(persona, symbol, raw, context)

    def _validate(self, persona: dict, symbol: str, raw: dict, context: dict) -> Opinion:
        try:
            stance = Stance(raw.get("stance", "neutral"))
        except ValueError:
            stance = Stance.NEUTRAL
        try:
            horizon = Horizon(raw.get("horizon", "swing"))
        except ValueError:
            horizon = Horizon.SWING
        return Opinion(
            sme=persona["id"],
            symbol=symbol,
            stance=stance,
            conviction=max(0.0, min(1.0, float(raw.get("conviction", 0.0)))),
            horizon=horizon,
            rationale=str(raw.get("rationale", "")),
            key_risks=list(raw.get("key_risks", []))[:6],
            suggested_size=max(0.0, min(1.0, float(raw.get("suggested_size", 0.0)))),
            evidence=context.get("evidence", {}),
        )

    @staticmethod
    def _persist(op: Opinion) -> None:
        with session_scope() as s:
            s.add(
                SmeOpinion(
                    sme=op.sme,
                    symbol=op.symbol,
                    stance=op.stance.value,
                    conviction=op.conviction,
                    horizon=op.horizon.value,
                    rationale=op.rationale,
                    key_risks=op.key_risks,
                    suggested_size=op.suggested_size,
                    evidence=op.evidence,
                )
            )


def _signals_hash(persona_id: str, symbol: str, signals: dict) -> str:
    body = json.dumps({"p": persona_id, "s": symbol, "sig": signals}, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()
