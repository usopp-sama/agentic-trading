"""Deep company-analysis toolkit (research).

Phase 1 (`disclosures`): locate + download the public documents an Indian
listed company must publish under SEBI LODR — quarterly results, earnings-call
transcripts, investor presentations, shareholding patterns, annual reports.

Phase 2 (`extractors`): turn those PDFs into structured signal — financial
highlights, forward guidance, risk factors, capex plans, management commentary.

Later phases layer an LLM "analyst" pass and wire the dossier into the SME
agents + dashboard. Kept out of the always-on services so it never blocks the
paper run; driven on demand via ``scripts/analyze_company.py``.
"""

from ats.services.research.disclosures import (
    Disclosure,
    DisclosureKind,
    DisclosureFetcher,
    LODR_CHECKLIST,
    research_dir,
)
from ats.services.research.extractors import analyze_document, extract_text

__all__ = [
    "Disclosure",
    "DisclosureKind",
    "DisclosureFetcher",
    "LODR_CHECKLIST",
    "research_dir",
    "analyze_document",
    "extract_text",
]
