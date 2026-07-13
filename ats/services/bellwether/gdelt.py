"""GDELT 2.0 DOC API client (Bellwether P1).

Free, no-key access to the global news database. We use two modes:
  * ``timelinetone`` / ``timelinevol`` -> a daily series of average TONE and
    article VOLUME for a query over a window (the tradeable signal).
  * ``artlist`` -> dated sample headlines (audit / relevance eyeballing).

The free API rate-limits by IP (HTTP 429) if you fire calls back-to-back — the
Phase-0 spike proved this — so the client enforces an inter-call ``delay`` and
retries 429/5xx with exponential backoff. Parsing is split from fetching so the
(pure) parsers are unit-tested without a network.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime

from ats.core.logging import get_logger

log = get_logger("ats.bellwether.gdelt")

_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltError(RuntimeError):
    """A GDELT call failed after retries (or returned no usable payload)."""


# --- pure parsers (no network; unit-tested) ---------------------------------
def parse_timeline(payload: dict) -> list[dict]:
    """GDELT ``timeline*`` JSON -> ``[{"date": 'YYYY-MM-DD', "value": float}]``.

    The API returns ``{"timeline": [{"series": ..., "data": [{"date": "20230101T000000Z",
    "value": 1.23}, ...]}]}``. Malformed points are skipped, not fatal."""
    out: list[dict] = []
    series = (payload or {}).get("timeline") or []
    if not series:
        return out
    for point in series[0].get("data", []) or []:
        raw = str(point.get("date", ""))
        try:
            d = _parse_gdelt_date(raw)
            out.append({"date": d.isoformat(), "value": float(point["value"])})
        except Exception:  # noqa: BLE001 - one bad point must not drop the series
            continue
    return out


def parse_artlist(payload: dict) -> list[dict]:
    """GDELT ``artlist`` JSON -> dated headline dicts."""
    out: list[dict] = []
    for a in (payload or {}).get("articles", []) or []:
        out.append({
            "seendate": str(a.get("seendate", "")),
            "title": (a.get("title", "") or "")[:200],
            "url": a.get("url", "") or "",
            "domain": a.get("domain", "") or "",
            "country": a.get("sourcecountry", "") or "",
        })
    return out


def _parse_gdelt_date(raw: str) -> date:
    """GDELT stamps look like ``20230101T000000Z`` (or ``20230101120000``)."""
    s = raw.strip().replace("Z", "").replace("T", "")
    if len(s) < 8:
        raise ValueError(f"short date {raw!r}")
    return datetime.strptime(s[:8], "%Y%m%d").date()


# --- client -----------------------------------------------------------------
class GdeltClient:
    """Rate-limit-aware GDELT DOC client.

    ``http_get`` is injectable for tests: a callable ``(url, params) -> (status,
    json_or_none, text)``. Defaults to httpx.
    """

    def __init__(self, *, delay: float = 6.0, max_retries: int = 4,
                 backoff: float = 8.0, timeout: float = 40.0,
                 http_get: Callable[[str, dict], tuple[int, dict | None, str]] | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.delay = max(0.0, delay)
        self.max_retries = max(0, max_retries)
        self.backoff = max(0.0, backoff)
        self.timeout = timeout
        self._http_get = http_get or self._httpx_get
        self._sleep = sleep
        self._last_call = 0.0

    def _httpx_get(self, url: str, params: dict) -> tuple[int, dict | None, str]:  # pragma: no cover - network
        import httpx

        resp = httpx.get(url, params=params, timeout=self.timeout,
                         headers={"User-Agent": "bellwether-collector/0.1"})
        body = None
        text = resp.text
        ctype = resp.headers.get("content-type", "")
        if resp.status_code == 200 and ("json" in ctype or text.lstrip().startswith("{")):
            try:
                body = resp.json()
            except Exception:  # noqa: BLE001
                body = None
        return resp.status_code, body, text

    def _throttle(self) -> None:
        wait = self.delay - (time.monotonic() - self._last_call)
        if wait > 0:
            self._sleep(wait)

    def get(self, params: dict) -> dict:
        """One GDELT call with inter-call throttle + 429/5xx backoff retry."""
        q = {"format": "json", "sourcelang": "english", **params}
        attempt = 0
        while True:
            self._throttle()
            status, body, text = self._http_get(_DOC_URL, q)
            self._last_call = time.monotonic()
            if status == 200 and body is not None:
                return body
            retryable = status == 429 or 500 <= status < 600
            if retryable and attempt < self.max_retries:
                wait = self.backoff * (2 ** attempt)
                log.warning("gdelt_retry", extra={"status": status, "attempt": attempt + 1,
                                                  "wait_s": round(wait, 1)})
                self._sleep(wait)
                attempt += 1
                continue
            raise GdeltError(f"GDELT {status} after {attempt} retries: {text[:160]}")

    # --- typed convenience calls ---
    @staticmethod
    def _win(query: str, start: date, end: date) -> dict:
        fmt = "%Y%m%d000000"
        return {"query": query,
                "startdatetime": start.strftime(fmt),
                "enddatetime": end.strftime(fmt)}

    def timeline_tone(self, query: str, start: date, end: date) -> list[dict]:
        return parse_timeline(self.get({**self._win(query, start, end),
                                        "mode": "timelinetone", "timelinesmooth": "0"}))

    def timeline_volume(self, query: str, start: date, end: date) -> list[dict]:
        return parse_timeline(self.get({**self._win(query, start, end),
                                        "mode": "timelinevol"}))

    def artlist(self, query: str, start: date, end: date, maxrecords: int = 25) -> list[dict]:
        return parse_artlist(self.get({**self._win(query, start, end),
                                       "mode": "artlist", "maxrecords": str(maxrecords),
                                       "sort": "datedesc"}))
