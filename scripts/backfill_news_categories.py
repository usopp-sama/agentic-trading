"""Backfill news categories over the existing archive (P3).

New items are categorized at ingest; this one-time (idempotent) pass classifies
everything already stored. Safe to re-run — it only writes rows whose category
would change.

    .venv/Scripts/python -m scripts.backfill_news_categories
"""

from __future__ import annotations

from sqlalchemy import select

from ats.core.db import init_db, session_scope
from ats.core.models import NewsItem
from ats.services.scraper.categorize import categorize


def main() -> int:
    init_db()
    changed = 0
    total = 0
    with session_scope() as s:
        for n in s.execute(select(NewsItem)).scalars().all():
            total += 1
            cat = categorize(n.title, n.body, n.tickers)
            if n.category != cat:
                n.category = cat
                changed += 1
    print(f"Categorized {total} news items ({changed} updated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
