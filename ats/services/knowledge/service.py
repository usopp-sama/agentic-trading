"""Knowledge Service.

Builds instrument profiles, indexes them in the vector store for RAG, serves
``get_profile`` (used by the get_instrument_profile tool and Family C SMEs),
and provides thematic-view-to-vehicle routing (given a theme, which instrument
best expresses it).
"""

from __future__ import annotations

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Instrument
from ats.services.knowledge.profiles import build_profile
from ats.services.nlp.vectorstore import get_vector_store

log = get_logger("ats.knowledge")


class KnowledgeService:
    name = "knowledge"

    def __init__(self) -> None:
        self._profiles: dict[str, dict] = {}
        self._store = get_vector_store()
        self._nlp = None

    async def start(self, ctx) -> None:
        self._nlp = ctx.orchestrator.get("nlp")
        with session_scope() as s:
            instruments = [
                (r.symbol, r.name, r.sector, r.instrument_type)
                for r in s.execute(select(Instrument)).scalars().all()
            ]
        for symbol, name, sector, itype in instruments:
            profile = build_profile(symbol, name, sector, itype)
            self._profiles[symbol] = profile
            self._store.add(
                doc_id=f"profile:{symbol}",
                text=profile["text"],
                metadata={"kind": "profile", "symbol": symbol, "themes": profile["themes"]},
            )
        log.info("profiles_indexed", extra={"count": len(self._profiles)})

    def get_profile(self, symbol: str) -> dict:
        profile = dict(self._profiles.get(symbol, {}))
        if not profile:
            return {}
        # Thematic fit: is this name's news flow currently supportive? (Proxy
        # until per-theme macro feeds land.) Profile-aware lens, not raw price.
        fit = 0.0
        if self._nlp is not None:
            fit = float(self._nlp.recent_sentiment(symbol).get("mean_score", 0.0))
        profile["thematic_fit"] = round(fit, 4)
        return profile

    def search_by_theme(self, theme: str, k: int = 5) -> list[dict]:
        hits = self._store.search(theme, k=k, where={"kind": "profile"})
        return [{"symbol": h["metadata"]["symbol"], "score": h["score"]} for h in hits]

    def route_view_to_vehicle(self, theme: str) -> dict | None:
        hits = self.search_by_theme(theme, k=1)
        return hits[0] if hits else None

    def all_profiles(self) -> dict[str, dict]:
        return dict(self._profiles)
