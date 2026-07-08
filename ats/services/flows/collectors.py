"""Public NSE flow-data collectors: delivery percentage + bulk deals.

Fetchers are best-effort (short timeout, browser-ish UA, empty result on any
failure) so an offline or blocked host degrades gracefully — the signature
then runs delivery-unconfirmed. Parsing is split from fetching so tests can
feed canned CSV without a network.

Sources (both public):
- ``sec_bhavdata_full_DDMMYYYY.csv`` — per-symbol turnover + DELIV_PER
- ``bulk.csv`` — rolling window of bulk-deal disclosures
"""

from __future__ import annotations

import csv
import io
from datetime import date

from ats.core.logging import get_logger

log = get_logger("ats.flows.collectors")

_BHAV_URL = "https://archives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
_BULK_URL = "https://archives.nseindia.com/content/equities/bulk.csv"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/csv,*/*",
}
_TIMEOUT_S = 20.0


def _get(url: str) -> str:
    import httpx

    with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT_S, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def to_yf_symbol(nse_symbol: str) -> str:
    """NSE bare symbol → the repo's yfinance convention."""
    return f"{nse_symbol.strip().upper()}.NS"


# --- delivery percentage ------------------------------------------------------------
def parse_bhavdata(text: str) -> list[dict]:
    """Rows of {symbol, delivery_pct} from a full-bhavcopy CSV (EQ series only)."""
    out: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        row = { (k or "").strip(): (v or "").strip() for k, v in row.items() }
        if row.get("SERIES", "") != "EQ":
            continue
        sym = row.get("SYMBOL", "")
        raw = row.get("DELIV_PER", "")
        if not sym or raw in ("", "-"):
            continue
        try:
            out.append({"symbol": to_yf_symbol(sym), "delivery_pct": float(raw)})
        except ValueError:
            continue
    return out


def fetch_delivery(day: date) -> list[dict]:
    """Delivery percentages for one trading day; [] on any failure."""
    url = _BHAV_URL.format(ddmmyyyy=day.strftime("%d%m%Y"))
    try:
        return parse_bhavdata(_get(url))
    except Exception as exc:  # noqa: BLE001 — collectors never raise
        log.info("delivery_fetch_failed", extra={"day": day.isoformat(), "error": str(exc)})
        return []


# --- bulk deals -----------------------------------------------------------------------
def parse_bulk_deals(text: str) -> list[dict]:
    """Rows of {symbol, day, side, qty} from the rolling bulk-deals CSV."""
    out: list[dict] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        row = { (k or "").strip(): (v or "").strip() for k, v in row.items() }
        sym = row.get("Symbol") or row.get("SYMBOL") or ""
        raw_day = row.get("Date") or row.get("DATE") or ""
        side = (row.get("Buy/Sell") or row.get("BUY/SELL") or "").upper()
        qty_raw = (row.get("Quantity Traded") or row.get("QTY") or "0").replace(",", "")
        if not sym or not raw_day:
            continue
        try:
            day = _parse_nse_date(raw_day)
            qty = float(qty_raw)
        except ValueError:
            continue
        out.append({
            "symbol": to_yf_symbol(sym), "day": day,
            "side": "BUY" if side.startswith("B") else "SELL", "qty": qty,
        })
    return out


def fetch_bulk_deals() -> list[dict]:
    """Recent bulk-deal disclosures (rolling window); [] on any failure."""
    try:
        return parse_bulk_deals(_get(_BULK_URL))
    except Exception as exc:  # noqa: BLE001
        log.info("bulk_deals_fetch_failed", extra={"error": str(exc)})
        return []


def _parse_nse_date(raw: str) -> date:
    """NSE CSVs use DD-MMM-YYYY (e.g. 07-JUL-2026)."""
    from datetime import datetime

    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unparseable NSE date: {raw!r}")
