"""Financial-statement provider + persistence.

Feeds ``FinancialStatements`` from either the live yfinance provider or a
manual/paid CSV export (same ``source`` field, same shape). The DB read/write
helpers are pure and unit-tested; the yfinance fetch is network-only and
isolated behind ``# pragma: no cover``. Everything degrades gracefully — a
symbol that fails to fetch simply contributes no rows, like the ratios
provider.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import FinancialStatements

log = get_logger("ats.statements")

# The statement lines we persist (must match FinancialStatements columns).
_METRICS = (
    "revenue", "ebit", "net_income", "gross_margin", "tax_rate",
    "cfo", "capex", "dna", "dividends_paid",
    "total_assets", "total_liabilities", "total_debt",
    "current_assets", "current_liabilities", "retained_earnings",
    "net_debt", "shares_outstanding",
)


@dataclass
class StatementSnapshot:
    symbol: str
    as_of: date
    period: str = "annual"
    source: str = "yfinance"
    revenue: float | None = None
    ebit: float | None = None
    net_income: float | None = None
    gross_margin: float | None = None
    tax_rate: float | None = None
    cfo: float | None = None
    capex: float | None = None
    dna: float | None = None
    dividends_paid: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_debt: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    retained_earnings: float | None = None
    net_debt: float | None = None
    shares_outstanding: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


# --- persistence (pure DB, unit-tested) ------------------------------------

def persist_statements(snaps: list[StatementSnapshot]) -> int:
    """Upsert snapshots on (symbol, period, as_of). Returns rows written."""
    written = 0
    with session_scope() as s:
        for snap in snaps:
            row = s.execute(
                select(FinancialStatements).where(
                    FinancialStatements.symbol == snap.symbol,
                    FinancialStatements.period == snap.period,
                    FinancialStatements.as_of == snap.as_of,
                )
            ).scalar_one_or_none()
            if row is None:
                row = FinancialStatements(
                    symbol=snap.symbol, period=snap.period, as_of=snap.as_of
                )
                s.add(row)
            for m in _METRICS:
                setattr(row, m, getattr(snap, m))
            row.source = snap.source
            written += 1
    return written


def latest_statements(
    symbol: str, period: str = "annual", n: int = 4
) -> list[dict]:
    """Most-recent ``n`` statements for a symbol, newest first, as plain dicts
    (keys match ``quant.analysis.quality`` inputs)."""
    with session_scope() as s:
        rows = s.execute(
            select(FinancialStatements)
            .where(
                FinancialStatements.symbol == symbol,
                FinancialStatements.period == period,
            )
            .order_by(FinancialStatements.as_of.desc())
            .limit(max(1, n))
        ).scalars().all()
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(r: FinancialStatements) -> dict:
    d = {"symbol": r.symbol, "period": r.period, "as_of": r.as_of, "source": r.source}
    for m in _METRICS:
        d[m] = getattr(r, m)
    return d


# --- fetch (network; isolated) ---------------------------------------------

def fetch_statements(symbol: str, source: str = "yfinance", years: int = 4) -> list[StatementSnapshot]:
    """Fetch up to ``years`` annual statements for ``symbol``.

    ``source="yfinance"`` reads income/balance/cashflow frames. Any failure
    yields ``[]`` (best-effort). ``source="none"`` never touches the network.
    """
    if source == "none":
        return []
    if source == "yfinance":
        return _fetch_yfinance(symbol, years)
    log.warning("statements_unknown_source", extra={"symbol": symbol, "source": source})
    return []


def _fetch_yfinance(symbol: str, years: int) -> list[StatementSnapshot]:  # pragma: no cover - network
    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        fin = t.financials          # income statement (columns = period-end dates)
        bs = t.balance_sheet
        cf = t.cashflow
    except Exception as exc:  # noqa: BLE001
        log.warning("statements_fetch_failed", extra={"symbol": symbol, "error": str(exc)})
        return []

    def pick(frame, *names):
        if frame is None or getattr(frame, "empty", True):
            return {}
        for name in names:
            if name in frame.index:
                return frame.loc[name]
        return {}

    cols = []
    for frame in (fin, bs, cf):
        if frame is not None and not getattr(frame, "empty", True):
            cols = list(frame.columns)
            break
    if not cols:
        return []

    rev = pick(fin, "Total Revenue", "TotalRevenue")
    ebit = pick(fin, "EBIT", "Operating Income", "OperatingIncome")
    ni = pick(fin, "Net Income", "NetIncome")
    gross = pick(fin, "Gross Profit", "GrossProfit")
    pretax = pick(fin, "Pretax Income", "PretaxIncome")
    tax = pick(fin, "Tax Provision", "TaxProvision", "Income Tax Expense")
    cfo = pick(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = pick(cf, "Capital Expenditure", "CapitalExpenditures")
    dna = pick(cf, "Depreciation And Amortization", "Depreciation")
    divs = pick(cf, "Cash Dividends Paid", "Dividends Paid", "CommonStockDividendPaid")
    ta = pick(bs, "Total Assets", "TotalAssets")
    tl = pick(bs, "Total Liabilities Net Minority Interest", "Total Liab")
    td = pick(bs, "Total Debt", "TotalDebt")
    ca = pick(bs, "Current Assets", "Total Current Assets")
    cl = pick(bs, "Current Liabilities", "Total Current Liabilities")
    re = pick(bs, "Retained Earnings", "RetainedEarnings")
    shares = pick(bs, "Ordinary Shares Number", "Share Issued", "Common Stock Shares Outstanding")

    def g(series, col):
        try:
            v = series.get(col) if hasattr(series, "get") else None
            if v is None:
                return None
            f = float(v)
            return f if f == f else None
        except Exception:  # noqa: BLE001
            return None

    out: list[StatementSnapshot] = []
    for col in cols[:years]:
        as_of = col.date() if hasattr(col, "date") else date.today()
        revenue = g(rev, col)
        gp = g(gross, col)
        gm = (gp / revenue) if (gp is not None and revenue not in (None, 0)) else None
        pt, tx = g(pretax, col), g(tax, col)
        tax_rate = (tx / pt) if (tx is not None and pt not in (None, 0)) else None
        cap = g(capex, col)
        out.append(StatementSnapshot(
            symbol=symbol, as_of=as_of, period="annual", source="yfinance",
            revenue=revenue, ebit=g(ebit, col), net_income=g(ni, col),
            gross_margin=gm, tax_rate=tax_rate,
            cfo=g(cfo, col), capex=None if cap is None else abs(cap),
            dna=g(dna, col), dividends_paid=g(divs, col),
            total_assets=g(ta, col), total_liabilities=g(tl, col), total_debt=g(td, col),
            current_assets=g(ca, col), current_liabilities=g(cl, col),
            retained_earnings=g(re, col), shares_outstanding=g(shares, col),
        ))
    return out


# expose the metric list for the CSV importer
STATEMENT_FIELDS = tuple(f.name for f in fields(StatementSnapshot))
