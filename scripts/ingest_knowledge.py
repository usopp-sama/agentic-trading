"""Knowledge ingestion pipeline (Phase 2).

Drop raw sources into ``library/`` (PDF / HTML / DOCX / TXT / MD) and run this
script to parse, clean, structure, and tag them into retrieval-ready notes under
``knowledge/`` (committed to git). The raw ``library/`` stays local; the cleaned
notes are the version-controlled SME library. The knowledge base picks those
notes up automatically on the next start (or via ``KnowledgeBase.ingest_all``).

Pipeline per file
-----------------
1. **Parse**     — extract raw text by file type (lazy parser imports).
2. **Clean**     — NFKC normalize, de-hyphenate wrapped words, drop page
                   numbers / repeated headers-footers, rejoin wrapped lines.
3. **Structure** — promote heuristic headings to ``##`` and split overlong
                   paragraphs on sentence boundaries so nothing is truncated by
                   the knowledge base chunker.
4. **Tag**       — emit a YAML front-matter block (family, source, doc_type,
                   date, reliability, tickers) that ``knowledge_base.py`` reads.

The family is inferred from the source's sub-folder (``library/family_b/...``)
or set with ``--family``. Output filenames are slugified and family-prefixed so
they sort and tag predictably.

Examples
--------
    # one-time, after dropping files into library/
    python scripts/ingest_knowledge.py

    # ingest a single file as a family-B (macro) source, tagged for a ticker
    python scripts/ingest_knowledge.py --src library/rbi_mpc.pdf \\
        --family B --tickers NIFTYBEES,BANKBEES

    # preview without writing
    python scripts/ingest_knowledge.py --dry-run

PDF/HTML/DOCX parsing needs optional deps — install on the ingest machine only:
    pip install pypdf trafilatura python-docx
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter
from datetime import date as _date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# Curated, cleaned notes live here and ARE committed to git (raw library/ is not).
_DEFAULT_OUT = _REPO_ROOT / "knowledge"

# Body blocks above this many characters are split on sentence boundaries so the
# knowledge base chunker (900-char cap) never truncates content mid-paragraph.
_MAX_BLOCK_CHARS = 800

_TEXT_EXTS = {".txt", ".md", ".markdown"}
_PDF_EXTS = {".pdf"}
_HTML_EXTS = {".html", ".htm"}
_DOCX_EXTS = {".docx"}
_SUPPORTED = _TEXT_EXTS | _PDF_EXTS | _HTML_EXTS | _DOCX_EXTS

_FAMILY_DIR = {
    "family_a": "A", "a": "A",
    "family_b": "B", "b": "B",
    "family_c": "C", "c": "C",
    "risk": "RISK", "family_risk": "RISK",
}
_FAMILY_PREFIX = {"A": "family_a", "B": "family_b", "C": "family_c", "RISK": "risk", "all": "shared"}

_DATE_RE = re.compile(r"(20\d{2})[-_.]?(0[1-9]|1[0-2])?[-_.]?(0[1-9]|[12]\d|3[01])?")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class IngestError(RuntimeError):
    """Raised when a file cannot be parsed (e.g. missing optional parser)."""


# --------------------------------------------------------------------------- #
# Parsing                                                                      #
# --------------------------------------------------------------------------- #
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    # Prefer pdfplumber: better layout/table fidelity for research papers and
    # financial reports. Fall back to pypdf when pdfplumber isn't installed.
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(path)) as pdf:
            return "\n\n".join((page.extract_text() or "") for page in pdf.pages)
    except ImportError:
        pass
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover - env dependent
        raise IngestError(
            "PDF support needs 'pdfplumber' or 'pypdf' (pip install pdfplumber)"
        ) from exc
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _read_html(path: Path) -> str:
    raw = _read_text(path)
    try:
        import trafilatura  # type: ignore

        extracted = trafilatura.extract(raw, include_comments=False, include_tables=True)
        if extracted:
            return extracted
    except ImportError:
        pass
    return _strip_html(raw)


def _strip_html(raw: str) -> str:
    from html import unescape
    from html.parser import HTMLParser

    skip = {"script", "style", "head", "noscript", "svg"}

    class _Extractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []
            self._skip_depth = 0

        def handle_starttag(self, tag: str, attrs: object) -> None:
            if tag in skip:
                self._skip_depth += 1
            elif tag in {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
                self.parts.append("\n")

        def handle_endtag(self, tag: str) -> None:
            if tag in skip and self._skip_depth:
                self._skip_depth -= 1

        def handle_data(self, data: str) -> None:
            if not self._skip_depth and data.strip():
                self.parts.append(data)

    parser = _Extractor()
    parser.feed(raw)
    return unescape("".join(parser.parts))


def _read_docx(path: Path) -> str:
    try:
        import docx  # type: ignore
    except ImportError as exc:  # pragma: no cover - env dependent
        raise IngestError("DOCX support needs 'python-docx' (pip install python-docx)") from exc
    document = docx.Document(str(path))
    return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())


def parse_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _TEXT_EXTS:
        return _read_text(path)
    if ext in _PDF_EXTS:
        return _read_pdf(path)
    if ext in _HTML_EXTS:
        return _read_html(path)
    if ext in _DOCX_EXTS:
        return _read_docx(path)
    raise IngestError(f"unsupported file type: {ext}")


# --------------------------------------------------------------------------- #
# Cleaning                                                                     #
# --------------------------------------------------------------------------- #
def _drop_boilerplate(lines: list[str]) -> list[str]:
    """Drop page-number-only lines and frequently repeated headers/footers."""
    freq = Counter(ln.strip() for ln in lines if ln.strip())
    # Short lines that recur many times are almost always running headers/footers.
    repeated = {ln for ln, n in freq.items() if n >= 4 and len(ln) <= 70}
    kept: list[str] = []
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            kept.append(ln)
            continue
        if re.fullmatch(r"\d{1,4}", stripped):  # bare page number
            continue
        if re.fullmatch(r"(?i)page\s+\d+(\s+of\s+\d+)?", stripped):
            continue
        if stripped in repeated:
            continue
        kept.append(ln)
    return kept


def clean_text(text: str) -> str:
    """Normalize raw extracted text into clean prose."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
    # De-hyphenate words split across a line break: "exam-\nple" -> "example".
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    lines = _drop_boilerplate(lines)
    text = "\n".join(lines)
    # Rejoin lines wrapped mid-sentence (prev ends lowercase/comma, next is
    # lowercase) into a single line; leaves paragraph breaks (blank lines) alone.
    text = re.sub(r"(?<=[a-z,;:])\n(?=[a-z])", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- #
# Structuring                                                                  #
# --------------------------------------------------------------------------- #
def _looks_like_heading(block: str) -> bool:
    if "\n" in block or len(block) > 80 or len(block) < 3:
        return False
    if re.match(r"(?i)^(chapter|section|part|annex(ure)?)\s+\w", block):
        return True
    if re.match(r"^\d+(\.\d+)*\.?\s+\S", block):  # "2.1 Title"
        return True
    if block.endswith((".", ",", ";")):
        return False
    words = block.split()
    if not words or len(words) > 12:
        return False
    capitalized = sum(1 for w in words if w[:1].isupper() or not w[:1].isalpha())
    return block.isupper() or capitalized / len(words) >= 0.6


def _split_long_block(block: str) -> list[str]:
    if len(block) <= _MAX_BLOCK_CHARS:
        return [block]
    out: list[str] = []
    current = ""
    for sentence in _SENTENCE_RE.split(block):
        if current and len(current) + len(sentence) + 1 > _MAX_BLOCK_CHARS:
            out.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current.strip():
        out.append(current.strip())
    return out


def to_markdown_sections(text: str) -> str:
    """Promote heuristic headings to ``##`` and keep blocks chunk-sized."""
    blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]
    out: list[str] = []
    for block in blocks:
        if _looks_like_heading(block):
            out.append(f"## {block.rstrip(':').strip()}")
        else:
            out.extend(_split_long_block(block))
    return "\n\n".join(out)


# --------------------------------------------------------------------------- #
# Tagging / front-matter                                                       #
# --------------------------------------------------------------------------- #
def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "note"


def infer_family_from_path(path: Path, src_root: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(src_root.resolve())
    except ValueError:
        rel = path
    for part in rel.parts[:-1]:
        fam = _FAMILY_DIR.get(part.lower())
        if fam:
            return fam
    return None


def infer_date(name: str) -> str | None:
    match = _DATE_RE.search(name)
    if not match:
        return None
    year, month, day = match.group(1), match.group(2), match.group(3)
    if year and month and day:
        return f"{year}-{month}-{day}"
    if year and month:
        return f"{year}-{month}"
    return year


def _yaml_scalar(value: str) -> str:
    # Quote values that could confuse a YAML parser; safe_load reads these back.
    if value == "" or re.search(r"[:#\[\]{}>|*&!%@`\"']", value) or value != value.strip():
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def build_front_matter(
    *,
    family: str,
    source: str,
    doc_type: str,
    reliability: int,
    date: str | None,
    tickers: list[str],
) -> str:
    lines = ["---", f"family: {family}", f"source: {_yaml_scalar(source)}",
             f"doc_type: {doc_type}", f"reliability: {reliability}"]
    if date:
        lines.append(f"date: {_yaml_scalar(date)}")
    tickers_yaml = "[" + ", ".join(_yaml_scalar(t) for t in tickers) + "]"
    lines.append(f"tickers: {tickers_yaml}")
    lines.append(f"ingested: {_date.today().isoformat()}")
    lines.append("---")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #
def _is_source(path: Path) -> bool:
    if path.suffix.lower() not in _SUPPORTED:
        return False
    if path.name.startswith("."):  # dotfiles / .gitkeep
        return False
    if path.name.lower() == "readme.md":  # folder docs, not knowledge
        return False
    return True


def iter_sources(src: Path) -> list[Path]:
    if src.is_file():
        return [src] if _is_source(src) else []
    return sorted(p for p in src.rglob("*") if p.is_file() and _is_source(p))


def ingest_file(
    path: Path,
    *,
    src_root: Path,
    out_dir: Path,
    family_override: str | None,
    reliability: int,
    tickers: list[str],
    dry_run: bool,
    overwrite: bool,
) -> tuple[Path | None, str]:
    raw = parse_file(path)
    cleaned = clean_text(raw)
    if len(cleaned) < 40:
        return None, "empty/too short after cleaning"
    body = to_markdown_sections(cleaned)

    family = family_override or infer_family_from_path(path, src_root) or "all"
    source = path.stem
    doc_type = path.suffix.lower().lstrip(".") or "txt"
    front_matter = build_front_matter(
        family=family,
        source=source,
        doc_type=doc_type,
        reliability=reliability,
        date=infer_date(path.name),
        tickers=tickers,
    )

    prefix = _FAMILY_PREFIX.get(family, "shared")
    out_path = out_dir / f"{prefix}_{slugify(source)}.md"
    if out_path.exists() and not overwrite:
        return out_path, "skipped (exists; use --overwrite)"
    if dry_run:
        return out_path, "dry-run (not written)"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(f"{front_matter}\n\n{body}\n", encoding="utf-8")
    blocks = body.count("\n\n") + 1
    return out_path, f"wrote ~{blocks} blocks, {len(body)} chars"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest raw sources into the SME knowledge base.")
    parser.add_argument("--src", default="library", help="source file or directory (default: library)")
    parser.add_argument("--out", default=None, help="output dir (default: committed knowledge/)")
    parser.add_argument(
        "--family", choices=["auto", "A", "B", "C", "RISK", "all"], default="auto",
        help="family tag; 'auto' infers from sub-folder, else 'all' (default: auto)",
    )
    parser.add_argument("--reliability", type=int, default=95, help="reliability 0-100 (default: 95)")
    parser.add_argument("--tickers", default="", help="comma-separated tickers to tag all outputs")
    parser.add_argument("--dry-run", action="store_true", help="parse + report without writing")
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing notes")
    args = parser.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"error: source not found: {src}", file=sys.stderr)
        print("hint: create it and drop PDFs/reports inside, e.g. library/family_b/rbi_mpc.pdf")
        return 2

    out_dir = Path(args.out) if args.out else _DEFAULT_OUT
    family_override = None if args.family == "auto" else args.family
    reliability = max(0, min(100, args.reliability))
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    sources = iter_sources(src)
    if not sources:
        print(f"no supported files under {src} (looked for: {', '.join(sorted(_SUPPORTED))})")
        return 1

    print(f"ingesting {len(sources)} file(s) -> {out_dir}{' (dry-run)' if args.dry_run else ''}\n")
    ok = 0
    failed = 0
    for path in sources:
        try:
            out_path, note = ingest_file(
                path,
                src_root=src,
                out_dir=out_dir,
                family_override=family_override,
                reliability=reliability,
                tickers=tickers,
                dry_run=args.dry_run,
                overwrite=args.overwrite,
            )
        except IngestError as exc:
            failed += 1
            print(f"  SKIP {path}: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAIL {path}: {exc}")
            continue
        ok += 1
        target = out_path.name if out_path else "-"
        print(f"  OK   {path}  ->  {target}  ({note})")

    print(f"\ndone: {ok} ingested, {failed} skipped/failed.")
    if not args.dry_run and ok:
        print("Restart the app (or re-run KnowledgeBase.ingest_all) to load the new notes.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
