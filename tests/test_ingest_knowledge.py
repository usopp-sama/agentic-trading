"""Tests for the knowledge ingestion pipeline (scripts/ingest_knowledge.py)
and the YAML front-matter parsing it relies on in the knowledge base.

These cover the pure transforms (clean -> structure -> tag) and an end-to-end
ingest of a generated note into a fresh in-memory knowledge base, so we verify
that front-matter actually drives family scoping, reliability, and tickers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.ingest_knowledge as ingest  # noqa: E402
from ats.services.agents.knowledge_base import (  # noqa: E402
    KnowledgeBase,
    _coerce_reliability,
    _coerce_tickers,
    _normalize_family,
    _parse_front_matter,
)
from ats.services.nlp.vectorstore import InMemoryVectorStore  # noqa: E402


# --------------------------------------------------------------------------- #
# Cleaning                                                                     #
# --------------------------------------------------------------------------- #
def test_clean_text_dehyphenates_and_rejoins_wrapped_lines():
    raw = "The infla-\ntion print was\nhigher than expected.\n\nNew para."
    cleaned = ingest.clean_text(raw)
    assert "inflation" in cleaned
    assert "infla-" not in cleaned
    # wrapped sentence is rejoined onto one line
    assert "higher than expected." in cleaned
    # paragraph break is preserved
    assert "\n\nNew para." in cleaned


def test_clean_text_drops_page_numbers_and_repeated_headers():
    pages = []
    for i in range(5):
        pages.append("Annual Report 2024")  # running header repeated on every page
        pages.append(f"Body content for page number {i} with enough text to keep.")
        pages.append(str(i + 1))  # bare page number
    cleaned = ingest.clean_text("\n".join(pages))
    assert "Annual Report 2024" not in cleaned
    assert "\n1\n" not in f"\n{cleaned}\n"
    assert "Body content for page" in cleaned


# --------------------------------------------------------------------------- #
# Structuring                                                                  #
# --------------------------------------------------------------------------- #
def test_looks_like_heading():
    assert ingest._looks_like_heading("Monetary Policy Outlook")
    assert ingest._looks_like_heading("2.1 Liquidity Measures")
    assert ingest._looks_like_heading("RISK FACTORS")
    assert not ingest._looks_like_heading("The committee decided to hold rates steady.")
    assert not ingest._looks_like_heading("a" * 200)


def test_long_blocks_are_split_under_chunk_cap():
    long_para = " ".join(f"Sentence number {i} about markets." for i in range(120))
    out = ingest.to_markdown_sections(long_para)
    blocks = [b for b in out.split("\n\n") if b.strip()]
    assert len(blocks) > 1
    assert all(len(b) <= ingest._MAX_BLOCK_CHARS + 80 for b in blocks)


def test_headings_promoted_to_markdown():
    text = "Monetary Policy\n\nThe MPC kept the repo rate unchanged at 6.5 percent."
    out = ingest.to_markdown_sections(text)
    assert out.startswith("## Monetary Policy")


# --------------------------------------------------------------------------- #
# Tagging                                                                      #
# --------------------------------------------------------------------------- #
def test_infer_family_from_path():
    root = Path("library")
    assert ingest.infer_family_from_path(root / "family_b" / "rbi.pdf", root) == "B"
    assert ingest.infer_family_from_path(root / "risk" / "sizing.pdf", root) == "RISK"
    assert ingest.infer_family_from_path(root / "loose.pdf", root) is None


def test_infer_date_and_slugify():
    assert ingest.infer_date("rbi_mpc_2024-04.pdf") == "2024-04"
    assert ingest.infer_date("report_2023-11-15.pdf") == "2023-11-15"
    assert ingest.infer_date("no_date_here.pdf") is None
    assert ingest.slugify("RBI MPC: April 2024!") == "rbi_mpc_april_2024"


def test_build_front_matter_is_valid_yaml():
    fm = ingest.build_front_matter(
        family="B", source="rbi: mpc", doc_type="pdf",
        reliability=95, date="2024-04", tickers=["NIFTYBEES", "BANKBEES"],
    )
    assert fm.startswith("---") and fm.rstrip().endswith("---")
    meta = yaml.safe_load(fm.strip("-\n"))
    assert meta["family"] == "B"
    assert meta["source"] == "rbi: mpc"  # colon survives round-trip
    assert meta["reliability"] == 95
    assert meta["tickers"] == ["NIFTYBEES", "BANKBEES"]


# --------------------------------------------------------------------------- #
# Knowledge-base front-matter parsing                                          #
# --------------------------------------------------------------------------- #
def test_parse_front_matter_splits_meta_and_body():
    doc = "---\nfamily: B\nreliability: 80\n---\n\n## Heading\n\nBody text."
    meta, body = _parse_front_matter(doc)
    assert meta == {"family": "B", "reliability": 80}
    assert body.lstrip().startswith("## Heading")


def test_parse_front_matter_absent_returns_original():
    doc = "## Heading\n\nNo front matter here."
    meta, body = _parse_front_matter(doc)
    assert meta == {}
    assert body == doc


def test_coercers():
    assert _normalize_family("b") == "B"
    assert _normalize_family("all") == "all"
    assert _normalize_family("bogus") is None
    assert _coerce_reliability("90", 50) == 90
    assert _coerce_reliability("oops", 50) == 50
    assert _coerce_reliability(250, 50) == 100
    assert _coerce_tickers("nifty, bank") == ["NIFTY", "BANK"]
    assert _coerce_tickers(["gold", "silver"]) == ["GOLD", "SILVER"]


# --------------------------------------------------------------------------- #
# End-to-end: ingest a generated note into a fresh KB                          #
# --------------------------------------------------------------------------- #
def test_kb_ingests_front_matter_metadata(tmp_path):
    note = (
        "---\n"
        "family: B\n"
        "source: rbi_mpc\n"
        "doc_type: pdf\n"
        "reliability: 97\n"
        "tickers: [NIFTYBEES]\n"
        "---\n\n"
        "## Monetary Policy\n\n"
        "The MPC held the repo rate at 6.5 percent amid sticky core inflation.\n"
    )
    (tmp_path / "family_b_rbi_mpc.md").write_text(note, encoding="utf-8")

    kb = KnowledgeBase(store=InMemoryVectorStore())
    kb._ingest_dir(tmp_path, builtin=False)

    assert len(kb) >= 1
    docs = list(kb.store._docs.values())
    meta = docs[0].metadata
    assert meta["family"] == "B"
    assert meta["source"] == "rbi_mpc"
    assert meta["reliability"] == 97
    assert meta["tickers"] == ["NIFTYBEES"]
    assert meta["doc_type"] == "pdf"

    # Front-matter-scoped retrieval reaches a family-B expert and not family A.
    assert kb.retrieve("repo rate inflation", family="B", k=3)
    assert kb.retrieve("repo rate inflation", family="A", k=3) == []
    # Ticker is indexed for symbol search.
    assert kb.store.search_symbol("NIFTYBEES")


def test_ingest_file_writes_note(tmp_path):
    src = tmp_path / "family_b"
    src.mkdir()
    raw = (
        "Monetary Policy Outlook\n\n"
        "The infla-\ntion trajectory remains\nelevated going into the year.\n"
    )
    (src / "rbi_2024-04.txt").write_text(raw, encoding="utf-8")
    out_dir = tmp_path / "knowledge"

    out_path, note = ingest.ingest_file(
        src / "rbi_2024-04.txt",
        src_root=tmp_path,
        out_dir=out_dir,
        family_override=None,
        reliability=95,
        tickers=["NIFTYBEES"],
        dry_run=False,
        overwrite=True,
    )
    assert out_path is not None and out_path.exists()
    assert out_path.name == "family_b_rbi_2024_04.md"
    written = out_path.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(written)
    assert meta["family"] == "B"
    assert meta["date"] == "2024-04"
    assert meta["tickers"] == ["NIFTYBEES"]
    assert "inflation" in body
