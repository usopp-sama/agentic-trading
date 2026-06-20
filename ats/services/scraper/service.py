"""Scraper Service.

Runs collectors on a schedule, sanitizes and de-duplicates items, links them
to instrument symbols, persists them, and publishes NEWS events. All collected
text is untrusted: it is sanitized and stored as data only (never executed or
treated as instructions).
"""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.models import Instrument, NewsItem
from ats.services.nlp.ner import TickerMapper
from ats.services.scraper.collectors import (
    MarketauxCollector,
    MockCollector,
    RssCollector,
)

log = get_logger("ats.scraper")

_WS_RE = re.compile(r"\s+")


def _sanitize(text: str, cap: int = 1000) -> str:
    if not text:
        return ""
    # Collapse whitespace and strip control chars; cap length.
    cleaned = _WS_RE.sub(" ", text).strip()
    cleaned = "".join(ch for ch in cleaned if ch == "\n" or ord(ch) >= 32)
    return cleaned[:cap]


class ScraperService:
    name = "scraper"

    def __init__(self) -> None:
        self._bus: EventBus | None = None
        self._mapper: TickerMapper | None = None
        self._collectors: list = []
        self._mock_fallback: MockCollector | None = None

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._mapper = TickerMapper()
        self._collectors = self._build_collectors()

        from ats.core.config import get_settings

        interval = get_settings().news_poll_interval_s
        ctx.scheduler.add_job(
            self.collect_once, "interval", seconds=interval,
            id="news_poll", max_instances=1, coalesce=True,
        )
        await self.collect_once()  # initial pull

    def _build_collectors(self) -> list:
        from ats.core.config import get_settings

        settings = get_settings()
        collectors: list = []
        # Real, live news first: a finance news API if a key is set, plus
        # credible Indian finance RSS feeds (always best-effort).
        if settings.marketaux_api_key:
            collectors.append(MarketauxCollector(settings.marketaux_api_key))
        collectors.append(RssCollector())

        # Mock is only an offline safety net - used when live feeds return
        # nothing this cycle (no network/keys), never mixed into real news.
        with session_scope() as s:
            universe = [
                (r.symbol, r.name, r.sector)
                for r in s.execute(
                    select(Instrument).where(Instrument.instrument_type != "INDEX")
                ).scalars().all()
            ]
        self._mock_fallback = MockCollector(universe, n=6)
        return collectors

    async def collect_once(self) -> int:
        if self._mapper is None:
            return 0
        published, collected = await self._run_collectors(self._collectors)
        # Only synthesize news if the live feeds returned NOTHING at all (true
        # offline). All-duplicates (collected>0, published==0) is normal and
        # must NOT trigger the mock fallback.
        if collected == 0 and self._mock_fallback is not None:
            log.info("news_live_empty_using_fallback")
            published, _ = await self._run_collectors([self._mock_fallback])
        if published:
            log.info("news_published", extra={"count": published})
        return published

    async def _run_collectors(self, collectors: list) -> tuple[int, int]:
        published = 0
        collected = 0
        for collector in collectors:
            try:
                items = collector.collect()
            except Exception as exc:  # noqa: BLE001
                log.warning("collector_failed", extra={"collector": collector.name, "error": str(exc)})
                continue
            collected += len(items)
            for raw in items:
                news_id = self._persist(raw)
                if news_id is None:
                    continue
                title = _sanitize(raw.get("title", ""))
                body = _sanitize(raw.get("body", ""))
                tickers = self._mapper.match(f"{title} {body}")
                if self._bus is not None:
                    await self._publish_news(news_id, title, body, tickers, raw)
                published += 1
        return published, collected

    async def _publish_news(self, news_id, title, body, tickers, raw) -> None:
        await self._bus.publish(
            Topic.NEWS,
            {
                "news_id": news_id, "title": title, "body": body, "tickers": tickers,
                "source": raw.get("source"), "url": raw.get("url"), "ts": raw.get("ts"),
            },
        )

    def _persist(self, raw: dict) -> int | None:
        title = _sanitize(raw.get("title", ""))
        body = _sanitize(raw.get("body", ""))
        url = raw.get("url", "")
        if not title:
            return None
        raw_hash = hashlib.sha256(f"{title}|{url}".encode()).hexdigest()
        tickers = self._mapper.match(f"{title} {body}") if self._mapper else []
        with session_scope() as s:
            exists = s.execute(
                select(NewsItem.id).where(NewsItem.raw_hash == raw_hash)
            ).scalar_one_or_none()
            if exists:
                return None
            item = NewsItem(
                source=raw.get("source", ""),
                url=url,
                title=title,
                body=body,
                tickers=tickers,
                raw_hash=raw_hash,
            )
            s.add(item)
            s.flush()
            return item.id
