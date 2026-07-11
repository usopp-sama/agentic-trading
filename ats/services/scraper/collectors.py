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

    def __init__(self, api_key: str, min_interval_s: float = 1200.0) -> None:
        self._key = api_key
        # Free tier is 100 requests/day; throttle so the ~288 daily news polls
        # don't blow the quota. RSS still runs every poll.
        self._min_interval = max(0.0, float(min_interval_s))
        self._last_call: float | None = None

    def collect(self) -> list[dict]:
        import time

        import httpx

        now = time.monotonic()
        if self._last_call is not None and (now - self._last_call) < self._min_interval:
            return []  # throttled to stay under the free-tier daily cap
        self._last_call = now

        try:
            resp = httpx.get(
                "https://api.marketaux.com/v1/news/all",
                params={
                    "countries": "in",
                    "filter_entities": "true",
                    "language": "en",
                    "limit": 3,  # free tier caps at 3 articles/request anyway
                    "api_token": self._key,
                },
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


# --- keyed news APIs (P-news): three free-tier sources, each self-throttled ---
# The scraper polls every ~300s (≈288/day); each collector gates itself to its
# own daily budget and bumps a per-source kv counter so the Ops Console can
# show credits used today. All degrade to [] on any failure.

def _bump_credit(name: str) -> None:
    try:
        from datetime import date as _date

        from ats.core import state

        key = "news_credits"
        cur = state.get_kv(key)
        today = _date.today().isoformat()
        if cur.get("day") != today:
            cur = {"day": today}
        cur[name] = int(cur.get(name, 0)) + 1
        state.set_kv(key, cur)
    except Exception:  # noqa: BLE001 — accounting must never break collection
        pass


class _KeyedApiCollector:  # pragma: no cover - network in collect(); _parse is tested
    """Shared throttle + fetch scaffolding for the keyed news APIs."""

    name = "keyed"

    def __init__(self, api_key: str, min_interval_s: float) -> None:
        self._key = api_key
        self._min_interval = max(0.0, float(min_interval_s))
        self._last_call: float | None = None

    def _throttled(self) -> bool:
        import time

        now = time.monotonic()
        if self._last_call is not None and (now - self._last_call) < self._min_interval:
            return True
        self._last_call = now
        return False

    def _get(self, url: str, params: dict) -> dict | None:
        import httpx

        try:
            resp = httpx.get(url, params=params, timeout=15.0)
            resp.raise_for_status()
            _bump_credit(self.name)
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            log.warning(f"{self.name}_failed", extra={"error": str(exc)})
            return None


class NewsApiCollector(_KeyedApiCollector):
    """newsapi.org — 100 req/day free; throttle ≈96/day (15 min)."""

    name = "newsapi"

    def __init__(self, api_key: str, min_interval_s: float = 900.0) -> None:
        super().__init__(api_key, min_interval_s)

    def collect(self) -> list[dict]:  # pragma: no cover - network
        if self._throttled():
            return []
        data = self._get(
            "https://newsapi.org/v2/top-headlines",
            {"country": "in", "category": "business", "pageSize": 20, "apiKey": self._key},
        )
        return self._parse(data) if data else []

    @staticmethod
    def _parse(data: dict) -> list[dict]:
        out = []
        for a in data.get("articles", []) or []:
            out.append({
                "source": f"newsapi:{(a.get('source') or {}).get('name', '')}",
                "url": a.get("url", "") or "",
                "title": a.get("title", "") or "",
                "body": a.get("description", "") or a.get("content", "") or "",
                "ts": a.get("publishedAt", datetime.now(timezone.utc).isoformat()),
            })
        return out


class NewsDataCollector(_KeyedApiCollector):
    """newsdata.io — 200 credits/day free (12 h delayed); throttle ≈96/day."""

    name = "newsdata"

    def __init__(self, api_key: str, min_interval_s: float = 900.0) -> None:
        super().__init__(api_key, min_interval_s)

    def collect(self) -> list[dict]:  # pragma: no cover - network
        if self._throttled():
            return []
        data = self._get(
            "https://newsdata.io/api/1/latest",
            {"apikey": self._key, "country": "in", "category": "business", "language": "en"},
        )
        return self._parse(data) if data else []

    @staticmethod
    def _parse(data: dict) -> list[dict]:
        out = []
        for a in data.get("results", []) or []:
            out.append({
                "source": f"newsdata:{a.get('source_id', '')}",
                "url": a.get("link", "") or "",
                "title": a.get("title", "") or "",
                "body": a.get("description", "") or "",
                "ts": a.get("pubDate", datetime.now(timezone.utc).isoformat()),
            })
        return out


class CurrentsCollector(_KeyedApiCollector):
    """currentsapi.services — free tier; throttle ≈144/day (10 min)."""

    name = "currents"

    def __init__(self, api_key: str, min_interval_s: float = 600.0) -> None:
        super().__init__(api_key, min_interval_s)

    def collect(self) -> list[dict]:  # pragma: no cover - network
        if self._throttled():
            return []
        data = self._get(
            "https://api.currentsapi.services/v1/latest-news",
            {"apiKey": self._key, "country": "IN", "category": "business", "language": "en"},
        )
        return self._parse(data) if data else []

    @staticmethod
    def _parse(data: dict) -> list[dict]:
        out = []
        for a in data.get("news", []) or []:
            out.append({
                "source": f"currents:{a.get('author', '') or 'wire'}",
                "url": a.get("url", "") or "",
                "title": a.get("title", "") or "",
                "body": a.get("description", "") or "",
                "ts": a.get("published", datetime.now(timezone.utc).isoformat()),
            })
        return out
