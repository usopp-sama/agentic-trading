"""Deep-analysis toolkit: disclosure classification + heuristic extraction."""

from __future__ import annotations

from ats.services.research.disclosures import DisclosureKind, classify
from ats.services.research.extractors import analyze_document, find_financial_highlights

# A compact stand-in for an earnings-call transcript / results PDF text.
_SAMPLE = """
Reliance Industries Q1 FY26 Earnings Call Transcript.
Mukesh Ambani, Chairman and Managing Director, said we are pleased with a
strong quarter. Revenue from operations rose to Rs 2,48,160 crore, up 12% YoY.
EBITDA was Rs 42,500 crore and profit after tax stood at Rs 18,200 crore.
EPS came in at Rs 27.5 for the quarter.
Going forward, we expect double digit growth in the retail segment and have
guidance of margin expansion in the coming year.
On capacity, we plan a capital expenditure of Rs 75,000 crore for the new
petrochemical plant and the greenfield expansion at Jamnagar.
Key risks include regulatory uncertainty and input cost pressure from currency
volatility, which could be a headwind to margins.
"""


def test_classify_by_filename_and_url():
    assert classify("RIL_Q1FY26_Transcript.pdf") == DisclosureKind.EARNINGS_TRANSCRIPT
    assert classify("https://x.com/investor-presentation.pdf") == DisclosureKind.INVESTOR_PRESENTATION
    assert classify("Shareholding_Pattern_Jun2026.xml") == DisclosureKind.SHAREHOLDING_PATTERN
    assert classify("Q1FY26_Financial_Results.pdf") == DisclosureKind.QUARTERLY_RESULTS
    assert classify("Annual-Report-2026.pdf") == DisclosureKind.ANNUAL_REPORT
    assert classify("random_doc.pdf") == DisclosureKind.OTHER


def test_financial_highlights_pulls_metrics():
    fh = find_financial_highlights(_SAMPLE)
    # Revenue, EBITDA, PAT and EPS should all be detected with their figures.
    assert "revenue" in fh and any("crore" in h.lower() for h in fh["revenue"])
    assert "ebitda" in fh
    assert "pat" in fh
    assert "eps" in fh


def test_analyze_document_sections():
    out = analyze_document(text=_SAMPLE)
    assert out["chars"] > 0 and out["sentences"] > 0
    # Guidance, risk and capex sentence finders each catch the relevant lines.
    assert any("expect" in g.lower() or "guidance" in g.lower() for g in out["guidance"])
    assert any("risk" in r.lower() or "headwind" in r.lower() for r in out["risks"])
    assert any("capex" in c.lower() or "expansion" in c.lower() or "capital expenditure" in c.lower()
               for c in out["capex_expansion"])
    assert out["management_commentary"]  # the Chairman quote


def test_movers_flags_large_swings():
    from ats.services.dashboard.summary import _movers

    positions = [
        {"symbol": "AAA", "qty": 10, "avg_price": 100.0, "unrealized_pnl": 60.0},   # +6%
        {"symbol": "BBB", "qty": 5, "avg_price": 200.0, "unrealized_pnl": 10.0},    # +1% (ignored)
        {"symbol": "CCC", "qty": 8, "avg_price": 50.0, "unrealized_pnl": -40.0},    # -10%
    ]
    movers = _movers(positions)
    syms = {m["symbol"] for m in movers}
    assert syms == {"AAA", "CCC"}
    # Sorted by absolute move, biggest first.
    assert movers[0]["symbol"] == "CCC"
