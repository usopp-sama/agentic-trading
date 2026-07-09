"""Tests for scripts/download_sources.py.

These cover the pure, network-free helpers: URL/scheme validation, family ->
folder mapping, extension guessing, slugified target paths, same-domain PDF
link extraction, and manifest parsing. The actual HTTP download path is not
exercised here (no network in tests).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.download_sources as dl  # noqa: E402


# --------------------------------------------------------------------------- #
# URL / scheme validation (SSRF-safety: only http/https absolute URLs)         #
# --------------------------------------------------------------------------- #
def test_is_allowed_url_accepts_http_https():
    assert dl.is_allowed_url("https://www.rbi.org.in/report.pdf")
    assert dl.is_allowed_url("http://stat.wharton.upenn.edu/x.pdf")


def test_is_allowed_url_rejects_other_schemes_and_relative():
    assert not dl.is_allowed_url("file:///etc/passwd")
    assert not dl.is_allowed_url("ftp://example.com/x.pdf")
    assert not dl.is_allowed_url("/relative/path.pdf")
    assert not dl.is_allowed_url("javascript:alert(1)")
    assert not dl.is_allowed_url("")


# --------------------------------------------------------------------------- #
# Family mapping + target path                                                 #
# --------------------------------------------------------------------------- #
def test_normalize_and_family_dir():
    assert dl.normalize_family("b") == "B"
    assert dl.normalize_family("RISK") == "RISK"
    assert dl.normalize_family(None) == "all"
    assert dl.normalize_family("bogus") == "all"
    assert dl.family_dir("A") == "family_a"
    assert dl.family_dir("RISK") == "risk"
    assert dl.family_dir("all") == ""


def test_target_path_places_family_and_slugifies(tmp_path):
    p = dl.target_path(tmp_path, "B", "RBI Monetary Policy Report", ".pdf")
    assert p == tmp_path / "family_b" / "rbi_monetary_policy_report.pdf"
    # 'all' family lands at the library root (no sub-folder).
    p_all = dl.target_path(tmp_path, "all", "Glossary", ".md")
    assert p_all == tmp_path / "glossary.md"


# --------------------------------------------------------------------------- #
# Extension guessing                                                           #
# --------------------------------------------------------------------------- #
def test_guess_extension_prefers_url_then_content_type():
    assert dl.guess_extension("https://x.com/a/b.pdf", None) == ".pdf"
    assert dl.guess_extension("https://x.com/a/b.docx", None) == ".docx"
    # no extension in URL -> fall back to content-type
    assert dl.guess_extension("https://x.com/download?id=9", "application/pdf") == ".pdf"
    assert dl.guess_extension("https://x.com/page", "text/html; charset=utf-8") == ".html"
    # unknown everything -> default to .pdf (these sources are mostly PDFs)
    assert dl.guess_extension("https://x.com/download", None) == ".pdf"


# --------------------------------------------------------------------------- #
# Document link extraction (mode: page)                                        #
# --------------------------------------------------------------------------- #
def test_extract_document_links_same_domain_only():
    html = """
        <a href="/reports/mpr-2024.pdf">MPR</a>
        <a href="https://www.rbi.org.in/abs/fsr.PDF">FSR</a>
        <a href="https://evil.example.com/leak.pdf">other host</a>
        <a href="/page.html">not a doc</a>
        <a href="reports/bulletin.pdf?ver=2">relative</a>
    """
    base = "https://www.rbi.org.in/publications/"
    links = dl.extract_document_links(html, base)
    assert "https://www.rbi.org.in/reports/mpr-2024.pdf" in links
    assert "https://www.rbi.org.in/abs/fsr.PDF" in links
    assert "https://www.rbi.org.in/publications/reports/bulletin.pdf?ver=2" in links
    # cross-domain and non-document links are excluded
    assert all("evil.example.com" not in link for link in links)
    assert all(not link.endswith(".html") for link in links)


def test_extract_document_links_matches_multiple_types():
    html = """
        <a href="/a.pdf">pdf</a>
        <a href="/b.docx">word</a>
        <a href="/c.xlsx">excel</a>
        <a href="/d.csv">data</a>
        <a href="/e.zip">archive (excluded)</a>
    """
    links = dl.extract_document_links(html, "https://x.org/")
    assert links == [
        "https://x.org/a.pdf",
        "https://x.org/b.docx",
        "https://x.org/c.xlsx",
        "https://x.org/d.csv",
    ]
    # zip is not a configured document type
    assert all(not link.endswith(".zip") for link in links)


def test_extract_document_links_respects_custom_exts():
    html = '<a href="/a.pdf">pdf</a> <a href="/b.docx">word</a>'
    links = dl.extract_document_links(html, "https://x.org/", exts=(".pdf",))
    assert links == ["https://x.org/a.pdf"]


def test_extract_document_links_dedupes():
    html = '<a href="/a.pdf">one</a> <a href="/a.pdf">dup</a>'
    links = dl.extract_document_links(html, "https://x.org/")
    assert links == ["https://x.org/a.pdf"]


# --------------------------------------------------------------------------- #
# Manifest parsing                                                             #
# --------------------------------------------------------------------------- #
def test_parse_manifest_reads_settings_and_sources():
    data = {
        "settings": {"rate_limit_s": 1.5, "respect_robots": False, "max_file_mb": 50},
        "sources": [
            {"name": "Paper A", "family": "a", "url": "https://x.org/a.pdf", "reliability": 92},
            {"name": "TODO B", "family": "B", "url": "", "enabled": False},
            {"bad": "no name"},  # dropped
        ],
    }
    m = dl.parse_manifest(data)
    assert m.settings.rate_limit_s == 1.5
    assert m.settings.respect_robots is False
    assert m.settings.max_file_mb == 50
    assert len(m.sources) == 2
    assert m.sources[0].name == "Paper A"
    assert m.sources[0].family == "A"
    assert m.sources[0].reliability == 92
    assert m.sources[0].enabled is True
    assert m.sources[1].enabled is False


def test_parse_manifest_defaults_when_empty():
    m = dl.parse_manifest({})
    assert m.sources == []
    assert m.settings.respect_robots is True
    assert m.settings.rate_limit_s == dl.Settings.rate_limit_s
    assert m.settings.document_exts == dl._DEFAULT_DOC_EXTS


def test_parse_manifest_normalizes_document_exts():
    m = dl.parse_manifest({"settings": {"document_exts": ["pdf", ".DOCX", "csv"]}})
    assert m.settings.document_exts == (".pdf", ".docx", ".csv")


def test_repo_manifest_loads_and_only_has_safe_urls():
    """The shipped scripts/sources.yaml must parse and contain no bad schemes."""
    manifest = dl.load_manifest(Path(dl._DEFAULT_MANIFEST))
    assert manifest.sources, "expected pre-filled sources"
    for src in manifest.sources:
        if src.url:
            assert dl.is_allowed_url(src.url), f"unsafe url for {src.name}: {src.url}"
