"""Phase 2 — turn a disclosure PDF into structured signal.

Heuristic, dependency-light extraction (no LLM): pull financial highlights,
forward guidance, risk factors, capex/expansion plans and management commentary
out of quarterly results, transcripts and presentations. A later phase feeds
this structured dossier to an LLM analyst and the SME agents.

Text extraction prefers ``pdfplumber`` (best layout fidelity) then ``pypdf``;
both are optional. Pass plain text directly to :func:`analyze_document` to run
the section finders with no PDF dependency at all (used by tests).
"""

from __future__ import annotations

import re

# --- money + metric patterns (Indian filings) ----------------------------- #
_NUM = r"[\d,]+(?:\.\d+)?"
_UNIT = r"(?:cr(?:ore)?|crores?|lakhs?|bn|billion|mn|million)?"
_MONEY = rf"(?:Rs\.?|₹|INR)?\s*{_NUM}\s*{_UNIT}"

_METRIC_PATTERNS: dict[str, str] = {
    "revenue": r"(?:revenue from operations|total income|total revenue|net sales|revenue)",
    "ebitda": r"ebitda",
    "pat": r"(?:profit after tax|net profit|pat|profit for the period)",
    "eps": r"(?:earnings per share|eps)",
    "margin": r"(?:ebitda margin|operating margin|net margin|margin)",
}

_GUIDANCE_KW = (
    "guidance", "outlook", "we expect", "expects", "anticipate", "going forward",
    "we aim", "we plan", "target", "we are confident", "in the coming", "next year",
    "next quarter", "full year", "fy2", "double digit", "growth of",
)
_RISK_KW = (
    "risk", "headwind", "uncertainty", "uncertain", "challenge", "pressure",
    "slowdown", "litigation", "regulatory", "adverse", "weak demand", "input cost",
    "currency", "volatility",
)
_CAPEX_KW = (
    "capex", "capital expenditure", "capacity", "expansion", "greenfield",
    "brownfield", "new plant", "commissioning", "investment of", "invest ",
    "debottleneck", "ramp-up", "ramp up",
)
_MGMT_KW = (
    "managing director", "chief executive", "ceo", "cfo", "chairman",
    "we believe", "we are pleased", "i would like", "our strategy", "our focus",
)


def extract_text(path: str) -> str:
    """Extract text from a PDF (or read a .txt/.htm directly)."""
    low = path.lower()
    if low.endswith((".txt", ".md")):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    if low.endswith((".htm", ".html")):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            raw = fh.read()
        return re.sub(r"<[^>]+>", " ", raw)
    # PDF: prefer pdfplumber, fall back to pypdf.
    try:
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except ImportError:
        pass
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except ImportError as exc:
        raise ImportError(
            "PDF extraction needs 'pdfplumber' or 'pypdf'. Install with: "
            ".venv/bin/python -m pip install pdfplumber  (or pypdf). "
            "Or pass a .txt export to analyze_document(text=...)."
        ) from exc


def _sentences(text: str) -> list[str]:
    # Normalise whitespace, then split on sentence boundaries.
    text = re.sub(r"\s+", " ", text)
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9₹])", text)
    return [s.strip() for s in raw if len(s.strip()) > 25]


def _match_sentences(sentences: list[str], keywords: tuple[str, ...], cap: int = 8) -> list[str]:
    out, seen = [], set()
    for s in sentences:
        low = s.lower()
        if any(k in low for k in keywords):
            key = low[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(s[:400])
            if len(out) >= cap:
                break
    return out


def find_financial_highlights(text: str) -> dict[str, list[str]]:
    """Sentences/fragments that state a headline metric with a figure."""
    sentences = _sentences(text)
    found: dict[str, list[str]] = {}
    for metric, pat in _METRIC_PATTERNS.items():
        rx = re.compile(rf"{pat}[^.]{{0,60}}?{_MONEY}", re.IGNORECASE)
        hits: list[str] = []
        for s in sentences:
            m = rx.search(s)
            if m:
                hits.append(m.group(0).strip()[:160])
            if len(hits) >= 4:
                break
        if hits:
            found[metric] = hits
    return found


def analyze_document(path: str | None = None, *, text: str | None = None) -> dict:
    """Structured dossier from one disclosure. Pass ``path`` (PDF/txt/html) or
    ``text`` directly."""
    if text is None:
        if not path:
            raise ValueError("Provide either path= or text=")
        text = extract_text(path)
    sentences = _sentences(text)
    return {
        "chars": len(text),
        "sentences": len(sentences),
        "financial_highlights": find_financial_highlights(text),
        "guidance": _match_sentences(sentences, _GUIDANCE_KW),
        "risks": _match_sentences(sentences, _RISK_KW),
        "capex_expansion": _match_sentences(sentences, _CAPEX_KW),
        "management_commentary": _match_sentences(sentences, _MGMT_KW, cap=5),
    }
