"""Phase 1 — locate and download a company's public disclosures.

What an NSE/BSE-listed company must publish (SEBI LODR), and why each matters
for analysis, is captured in ``LODR_CHECKLIST``. The richest sources for an
LLM/analyst are the **earnings-call transcript** (management's plans + Q&A) and
the **annual report's MD&A** (strategy, risks).

Auto-discovery from the exchanges (BSE/NSE corporate-announcement feeds) is
intentionally pluggable: those endpoints are rate-limited / anti-bot and may be
blocked by a corporate TLS-inspecting proxy (the same one that throttled the
FinBERT download), so the reliable v1 path is *operator-provided URLs* (copied
from the company's investor-relations page) or local PDFs. ``truststore`` is
injected so HTTPS works behind such proxies when downloads are allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ats.core.config import DATA_DIR
from ats.core.logging import get_logger

log = get_logger("ats.research")


class DisclosureKind(str, Enum):
    QUARTERLY_RESULTS = "quarterly_results"     # Reg 33 — financials, <=45 days
    EARNINGS_TRANSCRIPT = "earnings_transcript"  # Reg 30 — call transcript, <=5d
    INVESTOR_PRESENTATION = "investor_presentation"  # Reg 30 — before the call
    SHAREHOLDING_PATTERN = "shareholding_pattern"   # Reg 31 — <=21 days
    ANNUAL_REPORT = "annual_report"             # Reg 34 — incl. MD&A, BRSR
    GOVERNANCE_REPORT = "governance_report"     # Reg 27 — quarterly
    EVENT_DISCLOSURE = "event_disclosure"       # Reg 30 — within 24h
    OTHER = "other"


# Operator-facing checklist: what to look for and why. Printed by the CLI.
LODR_CHECKLIST: list[dict] = [
    {"kind": DisclosureKind.QUARTERLY_RESULTS, "regulation": "Reg 33",
     "cadence": "Quarterly, within 45 days (Q4 within 60)",
     "why": "Hard numbers: revenue, PAT, EBITDA, margins, segment splits, YoY/QoQ."},
    {"kind": DisclosureKind.EARNINGS_TRANSCRIPT, "regulation": "Reg 30",
     "cadence": "Within 5 working days of the earnings call",
     "why": "Richest source — management's plans, guidance, and analyst Q&A."},
    {"kind": DisclosureKind.INVESTOR_PRESENTATION, "regulation": "Reg 30",
     "cadence": "Before the earnings call",
     "why": "Strategy, segment outlook, capex plans, demand commentary."},
    {"kind": DisclosureKind.SHAREHOLDING_PATTERN, "regulation": "Reg 31",
     "cadence": "Quarterly, within 21 days",
     "why": "Promoter/FII/DII/public flows; promoter pledging is a red flag."},
    {"kind": DisclosureKind.ANNUAL_REPORT, "regulation": "Reg 34",
     "cadence": "Annual",
     "why": "MD&A (strategy + risks), board's report, BRSR (ESG), auditor's report."},
    {"kind": DisclosureKind.GOVERNANCE_REPORT, "regulation": "Reg 27",
     "cadence": "Quarterly",
     "why": "Board composition, committees — governance quality signals."},
    {"kind": DisclosureKind.EVENT_DISCLOSURE, "regulation": "Reg 30",
     "cadence": "Within 24 hours of the event",
     "why": "Catalysts: M&A, dividends, KMP changes, material contracts/orders."},
]

# Filename/URL heuristics → kind, so downloads self-classify.
_KIND_HINTS: list[tuple[DisclosureKind, tuple[str, ...]]] = [
    (DisclosureKind.EARNINGS_TRANSCRIPT, ("transcript", "earnings call", "concall", "con-call")),
    (DisclosureKind.INVESTOR_PRESENTATION, ("presentation", "investor", "analyst", "ppt", "deck")),
    (DisclosureKind.SHAREHOLDING_PATTERN, ("shareholding", "shp", "holding pattern")),
    (DisclosureKind.QUARTERLY_RESULTS, ("result", "financial", "q1", "q2", "q3", "q4", "quarter")),
    (DisclosureKind.ANNUAL_REPORT, ("annual", "annualreport", "ar20", "ar-20", "integrated report")),
    (DisclosureKind.GOVERNANCE_REPORT, ("governance", "cg report")),
]


def classify(name_or_url: str) -> DisclosureKind:
    low = (name_or_url or "").lower()
    for kind, hints in _KIND_HINTS:
        if any(h in low for h in hints):
            return kind
    return DisclosureKind.OTHER


@dataclass
class Disclosure:
    symbol: str
    kind: DisclosureKind
    title: str
    url: str | None = None
    local_path: str | None = None
    fiscal_period: str | None = None   # e.g. "Q1FY26"
    meta: dict = field(default_factory=dict)


def research_dir(symbol: str) -> Path:
    """Per-symbol folder under ``var/research/`` for downloaded documents."""
    safe = "".join(c for c in symbol.upper() if c.isalnum() or c in "._-")
    d = DATA_DIR / "research" / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


class DisclosureFetcher:
    """Downloads operator-provided document URLs into the per-symbol folder.

    Auto-discovery against exchange feeds can be added behind ``discover()``
    later; v1 takes explicit URLs so it works reliably behind proxies.
    """

    def __init__(self, *, allow_download: bool = True, timeout_s: float = 60.0) -> None:
        self.allow_download = allow_download
        self.timeout_s = timeout_s

    def _session(self):
        # Use the OS trust store so HTTPS works behind a TLS-inspecting proxy.
        try:
            import truststore

            truststore.inject_into_ssl()
        except Exception:  # noqa: BLE001 - optional; default certs still work
            pass
        import requests

        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 (ATS-Research)"})
        return s

    def download(self, symbol: str, url: str, *, fiscal_period: str | None = None) -> Disclosure:
        kind = classify(url)
        dest_dir = research_dir(symbol)
        fname = url.split("?")[0].rstrip("/").split("/")[-1] or f"{kind.value}.pdf"
        if not fname.lower().endswith((".pdf", ".htm", ".html", ".xml")):
            fname += ".pdf"
        dest = dest_dir / fname
        if not self.allow_download:
            log.info("download_skipped", extra={"symbol": symbol, "url": url})
            return Disclosure(symbol, kind, fname, url=url, fiscal_period=fiscal_period,
                              meta={"downloaded": False})
        sess = self._session()
        with sess.get(url, stream=True, timeout=self.timeout_s) as r:
            r.raise_for_status()
            size = 0
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        fh.write(chunk)
                        size += len(chunk)
        log.info("disclosure_downloaded",
                 extra={"symbol": symbol, "kind": kind.value, "bytes": size, "path": str(dest)})
        return Disclosure(symbol, kind, fname, url=url, local_path=str(dest),
                          fiscal_period=fiscal_period, meta={"bytes": size})

    def fetch_many(self, symbol: str, urls: list[str]) -> list[Disclosure]:
        out: list[Disclosure] = []
        for u in urls:
            try:
                out.append(self.download(symbol, u))
            except Exception as exc:  # noqa: BLE001 - one bad URL shouldn't abort the batch
                log.warning("disclosure_fetch_failed", extra={"url": u, "error": str(exc)})
                out.append(Disclosure(symbol, classify(u), u.split("/")[-1], url=u,
                                      meta={"error": str(exc)}))
        return out
