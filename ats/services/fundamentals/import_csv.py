"""CSV importer for financial statements (manual / paid exports).

Lets the operator feed statement lines from a screener.in / investing.com /
broker export without any scraping or code change — the legitimate way to use a
paid data subscription (the operator downloads, we ingest the file).

CSV schema (header row; one row per symbol-period-year):

    symbol,period,as_of,revenue,ebit,net_income,gross_margin,tax_rate,cfo,
    capex,dna,dividends_paid,total_assets,total_liabilities,total_debt,
    current_assets,current_liabilities,retained_earnings,net_debt,
    shares_outstanding,source

Only ``symbol`` and ``as_of`` (YYYY-MM-DD) are required; ``period`` defaults to
"annual", ``source`` to "csv". Blank cells become ``None`` (missing stays
missing). Unknown columns are ignored.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

from ats.core.logging import get_logger
from ats.services.fundamentals.statements import StatementSnapshot, _METRICS

log = get_logger("ats.statements.csv")


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    v = v.strip().replace(",", "")
    if v == "" or v.lower() in ("na", "n/a", "none", "nan", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _to_date(v: str) -> date:
    v = v.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unparseable as_of date: {v!r}")


def parse_statements_csv(text: str) -> list[StatementSnapshot]:
    """Parse CSV text into snapshots. Rows missing symbol/as_of are skipped."""
    snaps: list[StatementSnapshot] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):  # header is line 1
        row = { (k or "").strip().lower(): v for k, v in row.items() }
        symbol = (row.get("symbol") or "").strip()
        as_of_raw = (row.get("as_of") or "").strip()
        if not symbol or not as_of_raw:
            log.warning("statements_csv_row_skipped", extra={"line": i})
            continue
        try:
            as_of = _to_date(as_of_raw)
        except ValueError as exc:
            log.warning("statements_csv_bad_date", extra={"line": i, "error": str(exc)})
            continue
        kwargs = {m: _to_float(row.get(m)) for m in _METRICS}
        snaps.append(StatementSnapshot(
            symbol=symbol,
            as_of=as_of,
            period=(row.get("period") or "annual").strip() or "annual",
            source=(row.get("source") or "csv").strip() or "csv",
            **kwargs,
        ))
    return snaps


def import_statements_file(path: str) -> list[StatementSnapshot]:
    with open(path, "r", encoding="utf-8-sig") as fh:
        return parse_statements_csv(fh.read())
