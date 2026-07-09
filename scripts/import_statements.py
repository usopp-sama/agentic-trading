"""Import financial statements from a CSV export into the DB.

Usage:
    .venv/Scripts/python -m scripts.import_statements path/to/statements.csv

The CSV schema is documented in ``ats.services.fundamentals.import_csv``. This
is the sanctioned way to load a paid/manual data export (screener.in,
investing.com Pro export, broker research) — download the file, run this, done.
No scraping, no network.
"""

from __future__ import annotations

import sys

from ats.core.db import init_db
from ats.services.fundamentals.import_csv import import_statements_file
from ats.services.fundamentals.statements import persist_statements


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = argv[0]
    init_db()
    snaps = import_statements_file(path)
    if not snaps:
        print(f"No valid rows found in {path}")
        return 1
    written = persist_statements(snaps)
    symbols = sorted({s.symbol for s in snaps})
    print(f"Imported {written} statement rows for {len(symbols)} symbols: "
          f"{', '.join(symbols[:20])}{' …' if len(symbols) > 20 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
