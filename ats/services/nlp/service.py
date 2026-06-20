"""NLP Service.

Subscribes to NEWS events, scores sentiment, persists per-symbol sentiment,
indexes the article in the vector store for RAG, and publishes SENTIMENT
events. Exposes per-symbol sentiment aggregation and RAG search used by agents.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import NewsItem, SentimentScore
from ats.services.nlp.sentiment import SentimentModel
from ats.services.nlp.vectorstore import get_vector_store

log = get_logger("ats.nlp")

# Pseudo-symbol carrying the overall, market-wide news mood (world/macro flow).
_MARKET = "MARKET"


class NlpService:
    name = "nlp"

    def __init__(self) -> None:
        self.model = SentimentModel(prefer_finbert=False)
        self.store = get_vector_store()
        self._bus: EventBus | None = None

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        ctx.bus.subscribe(Topic.NEWS, self._on_news)

    async def _on_news(self, evt) -> None:
        p = evt.payload
        tickers = p.get("tickers", [])
        text = f"{p.get('title', '')} {p.get('body', '')}".strip()
        label, score = self.model.score(text)

        self.store.add(
            doc_id=f"news:{p.get('news_id')}",
            text=text,
            metadata={
                "news_id": p.get("news_id"),
                "tickers": tickers,
                "source": p.get("source"),
                "label": label,
                "score": score,
                "ts": p.get("ts"),
            },
        )

        # Persist per-ticker scores AND a market-wide "MARKET" row for every
        # item — so world/macro news with no specific ticker still moves the
        # overall market-mood signal the macro (Family B) experts consume.
        with session_scope() as s:
            for symbol in [*tickers, _MARKET]:
                s.add(
                    SentimentScore(
                        symbol=symbol,
                        news_id=p.get("news_id"),
                        model="vader",
                        label=label,
                        score=score,
                    )
                )
        if self._bus is not None:
            await self._bus.publish(
                Topic.SENTIMENT,
                {"tickers": tickers, "label": label, "score": score, "news_id": p.get("news_id")},
            )

    # --- accessors used by agents -----------------------------------------
    def recent_sentiment(self, symbol: str, hours: int = 72) -> dict:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        with session_scope() as s:
            rows = s.execute(
                select(SentimentScore).where(
                    SentimentScore.symbol == symbol, SentimentScore.ts >= cutoff
                )
            ).scalars().all()
        if not rows:
            return {"symbol": symbol, "count": 0, "mean_score": 0.0, "label": "neutral"}
        scores = [r.score for r in rows]
        mean = sum(scores) / len(scores)
        label = "positive" if mean >= 0.2 else "negative" if mean <= -0.2 else "neutral"
        return {
            "symbol": symbol,
            "count": len(rows),
            "mean_score": round(mean, 4),
            "label": label,
        }

    def market_sentiment(self, hours: int = 48) -> dict:
        """Overall, market-wide news mood (the ``MARKET`` pseudo-symbol)."""
        return self.recent_sentiment(_MARKET, hours=hours)

    def recent_news(self, k: int = 5) -> list[dict]:
        """Latest headlines regardless of ticker — the world/market news feed
        the macro experts read. Returns lightweight dicts (no body)."""
        with session_scope() as s:
            rows = (
                s.execute(select(NewsItem).order_by(NewsItem.id.desc()).limit(max(1, k)))
                .scalars()
                .all()
            )
            return [
                {
                    "text": f"{r.title}. {(r.body or '')[:160]}".strip(),
                    "title": r.title,
                    "source": r.source,
                    "tickers": r.tickers or [],
                    "ts": r.ts.isoformat() if r.ts else None,
                }
                for r in rows
            ]

    def search(self, query: str, k: int = 5) -> list[dict]:
        return self.store.search(query, k)

    def search_symbol(self, symbol: str, k: int = 5) -> list[dict]:
        return self.store.search_symbol(symbol, k)
