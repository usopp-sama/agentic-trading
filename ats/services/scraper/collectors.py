"""News collectors.

Each collector returns a list of raw items:
    {"source", "url", "title", "body", "ts"}

- ``MockCollector``: deterministic, offline headlines referencing the universe,
  so the whole NLP -> agent pipeline runs with no network or keys.
- ``RssCollector``: best-effort pull from credible Indian finance RSS feeds.
- ``MarketauxCollector``: finance news API (used only if a key is configured).

All external content is treated as untrusted input downstream (sanitized
before storage and never interpreted as instructions by agents).
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Protocol

from ats.core.logging import get_logger

log = get_logger("ats.scraper")

# Credible Indian finance RSS feeds.
RSS_FEEDS = [
    ("Moneycontrol", "https://www.moneycontrol.com/rss/latestnews.xml"),
    ("EconomicTimes", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("BusinessStandard", "https://www.business-standard.com/rss/markets-106.rss"),
    ("LiveMint", "https://www.livemint.com/rss/markets"),
    ("BusinessLine", "https://www.thehindubusinessline.com/markets/feeder/default.rss"),
]


class Collector(Protocol):
    name: str

    def collect(self) -> list[dict]: ...


class MockCollector:
    """Deterministic synthetic news for offline dev."""

    name = "mock"

    _TEMPLATES = [
        ("{name} posts strong quarterly results, beats estimates", "positive"),
        ("{name} shares surge on robust demand outlook", "positive"),
        ("{name} wins large order, management upbeat on growth", "positive"),
        ("{name} hit by margin pressure, guidance cut", "negative"),
        ("{name} faces regulatory probe, stock under pressure", "negative"),
        ("{name} disappoints on weak volumes, analysts downgrade", "negative"),
        ("{name} announces buyback and dividend", "positive"),
        ("{name} flat as broader market consolidates", "neutral"),
        ("{sector} sector rallies on policy tailwinds", "positive"),
        ("{sector} stocks slip on global growth worries", "negative"),
    ]

    def __init__(self, universe: list[tuple[str, str, str]], n: int = 6, seed: int | None = None) -> None:
        # universe items: (symbol, name, sector)
        self._universe = universe
        self._n = n
        self._rng = random.Random(seed)

    def collect(self) -> list[dict]:
        items = []
        now = datetime.now(timezone.utc)
        for _ in range(self._n):
            sym, name, sector = self._rng.choice(self._universe)
            template, _tone = self._rng.choice(self._TEMPLATES)
            title = template.format(name=name, sector=sector)
            items.append(
                {
                    "source": "mock",
                    "url": f"mock://news/{abs(hash(title)) % 10_000_000}",
                    "title": title,
                    "body": title + ".",
                    "ts": now.isoformat(),
                }
            )
        return items


class RssCollector:
    name = "rss"

    def __init__(self, feeds: list[tuple[str, str]] | None = None, max_items: int = 20) -> None:
        self._feeds = feeds or RSS_FEEDS
        self._max = max_items

    def collect(self) -> list[dict]:
        try:
            import feedparser
        except ImportError:  # pragma: no cover
            return []
        items: list[dict] = []
        for source, url in self._feeds:
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[: self._max]:
                    items.append(
                        {
                            "source": source,
                            "url": getattr(entry, "link", ""),
                            "title": getattr(entry, "title", ""),
                            "body": getattr(entry, "summary", ""),
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                    )
            except Exception as exc:  # noqa: BLE001 - best-effort, network may be down
                log.warning("rss_fetch_failed", extra={"source": source, "error": str(exc)})
        return items


class MarketauxCollector:  # pragma: no cover - requires API key + network
    name = "marketaux"

    def __init__(self, api_key: str) -> None:
        self._key = api_key

    def collect(self) -> list[dict]:
        import httpx

        try:
            resp = httpx.get(
                "https://api.marketaux.com/v1/news/all",
                params={"countries": "in", "filter_entities": "true", "language": "en", "api_token": self._key},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except Exception as exc:  # noqa: BLE001
            log.warning("marketaux_failed", extra={"error": str(exc)})
            return []
        return [
            {
                "source": "marketaux",
                "url": d.get("url", ""),
                "title": d.get("title", ""),
                "body": d.get("description", "") or d.get("snippet", ""),
                "ts": d.get("published_at", datetime.now(timezone.utc).isoformat()),
            }
            for d in data
        ]
