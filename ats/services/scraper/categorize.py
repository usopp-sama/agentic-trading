"""Deterministic news categorization (P3).

An investing.com-style taxonomy assigned at ingest by keyword/regex rules — no
LLM. One category per item: the first rule that matches, in priority order
(``breaking`` first so a high-impact headline is never buried under a generic
tag). Falls back to ``stock_markets``. Pure function, unit-tested by fixtures.
"""

from __future__ import annotations

import re

# Display order + the canonical set (no "Pro News" — that's a paywall tier).
CATEGORIES = [
    "breaking", "earnings", "analyst_ratings", "ipo",
    "economic_indicators", "economy", "commodities", "currencies",
    "crypto", "stock_markets",
]

# (category, pattern) in priority order — first match wins.
_RULES: list[tuple[str, str]] = [
    ("breaking",
     r"acquisition|acquires|to acquire|takeover|merger|bankruptc|insolvenc|"
     r"fraud|sebi (order|bar|prob|penal)|raid|resign|steps down|default|"
     r"trading halt|fda approval|recall|data breach|hack"),
    ("earnings",
     r"\bq[1-4]\b|quarterly result|net profit|revenue (ros|fell|up|down|grew)|"
     r"earnings|guidance|ebitda|profit (ros|jump|fell|declin)|pat |margin"),
    ("analyst_ratings",
     r"upgrade|downgrade|target price|price target|\brating\b|buy call|sell call|"
     r"outperform|underperform|overweight|underweight|initiat(e|ed) coverage|reiterat"),
    ("ipo",
     r"\bipo\b|initial public offering|\bdrhp\b|listing (gain|debut|premium)|"
     r"grey market|\bgmp\b|subscribed \d|anchor investor"),
    ("economic_indicators",
     r"\bcpi\b|inflation|\bgdp\b|\biip\b|\bpmi\b|\bwpi\b|repo rate|jobless|"
     r"unemployment|trade deficit|fiscal deficit|rbi (mpc|policy|governor)"),
    ("economy",
     r"\beconomy\b|union budget|fiscal|tariff|subsid|ministry|parliament|"
     r"gst council|government (spend|borrow)"),
    ("commodities",
     r"\bgold\b|\bsilver\b|crude|brent|\bwti\b|oil price|natural gas|copper|"
     r"aluminium|\bzinc\b|commodit|bullion"),
    ("currencies",
     r"\brupee\b|forex|dollar index|usd/inr|currency|exchange rate|\byen\b|\beuro\b"),
    ("crypto",
     r"bitcoin|\bbtc\b|ethereum|\beth\b|crypto|blockchain|altcoin|stablecoin"),
]

_COMPILED = [(cat, re.compile(pat, re.IGNORECASE)) for cat, pat in _RULES]

_DEFAULT = "stock_markets"


def categorize(title: str, body: str = "", tickers: list | None = None) -> str:
    """Return one category for a news item (first matching rule, else
    ``stock_markets``)."""
    text = f"{title or ''} {body or ''}"
    for cat, rx in _COMPILED:
        if rx.search(text):
            return cat
    return _DEFAULT
