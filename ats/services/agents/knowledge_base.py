"""Domain knowledge base for SME grounding (RAG).

Turns each expert family into something that reasons with real domain material
instead of only live numbers — the "extensively knowledgeable" effect without
fine-tuning a model. Built-in primers ship in ``corpus/`` (one per family); you
can drop your own ``.md``/``.txt`` notes, research, or filings into a knowledge
directory (``ATS_KNOWLEDGE_DIR``, default ``var/knowledge``) to extend any
expert's reading.

Storage reuses the dependency-free in-memory vector store (hashed bag-of-words +
cosine), so retrieval works fully offline with zero setup. If you later install
``sentence-transformers`` + ``chromadb`` and set ``ATS_VECTOR_STORE=chroma`` the
same interface upgrades transparently.

Documents are chunked by paragraph and tagged with the family they belong to
(``A``/``B``/``C``/``RISK``) or ``all`` for shared material. Retrieval returns
the most relevant chunks for a query, scoped to the asking expert's family plus
the shared pool.

Notes may carry a YAML front-matter block to set ``family``, ``reliability``,
``tickers``, ``date``, ``doc_type`` and ``source`` explicitly — this is what
``scripts/ingest_knowledge.py`` writes when cleaning raw PDFs/HTML/DOCX into
``var/knowledge``. Files without front-matter still work (family is inferred
from the filename prefix).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from ats.core.config import get_settings
from ats.core.logging import get_logger
from ats.services.nlp.vectorstore import InMemoryVectorStore, get_vector_store

log = get_logger("ats.knowledge_base")

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
# Curated, cleaned notes produced by scripts/ingest_knowledge.py. Committed to
# git (the raw library/ sources are not) so the maintained SME library ships and
# deploys with the repo. parents[3] == repo root.
REPO_KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "knowledge"

# Filename prefix -> family tag. Anything else is shared ("all").
_FAMILY_PREFIX = {
    "family_a": "A",
    "family_b": "B",
    "family_c": "C",
    "risk": "RISK",
}

_MAX_CHUNK_CHARS = 900

# Reliability tiers (0-100) scale retrieval scores so trusted sources outrank
# generic ones. Directives (authored rules) sit at 100 (see directives.py).
_RELIABILITY_BUILTIN = 90   # shipped domain primers
_RELIABILITY_USER = 95      # operator-supplied notes/research/filings
_RELIABILITY_PROFILE = 88   # generated instrument profiles


def _family_for(filename: str) -> str:
    stem = filename.lower()
    for prefix, fam in _FAMILY_PREFIX.items():
        if stem.startswith(prefix):
            return fam
    return "all"


_FRONT_MATTER_RE = re.compile(r"^\ufeff?---[ \t]*\n(.*?)\n---[ \t]*\n", re.S)
_VALID_FAMILIES = {"A", "B", "C", "RISK", "all"}


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """Split a leading YAML front-matter block (``--- ... ---``) from the body.

    Returns ``({}, text)`` when there is no valid front-matter so plain notes
    keep working unchanged. YAML is parsed with ``safe_load`` only.
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[match.end():]


def _normalize_family(value: object) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    if not token:
        return None
    upper = token.upper()
    if upper == "ALL":
        return "all"
    return upper if upper in _VALID_FAMILIES else None


def _coerce_reliability(value: object, default: int) -> int:
    try:
        score = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(0, min(100, score))


def _coerce_tickers(value: object) -> list[str]:
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple)):
        items = [str(v) for v in value]
    else:
        return []
    return [t.strip().upper() for t in items if str(t).strip()]


def _chunk(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) chunks by paragraph, carrying the
    nearest preceding heading so each chunk is self-describing."""
    chunks: list[tuple[str, str]] = []
    heading = ""
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            chunks.append((heading, body[:_MAX_CHUNK_CHARS]))

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            buf = []
            heading = line.lstrip("#").strip()
        elif not line.strip():
            flush()
            buf = []
        else:
            buf.append(line.strip())
    flush()
    return chunks


class KnowledgeBase:
    def __init__(self, store: InMemoryVectorStore | None = None) -> None:
        self.store = store or get_vector_store()
        self._count = 0
        self._loaded = False

    def ingest_all(self, knowledge_service: object | None = None) -> int:
        """Idempotent: load built-in corpus + user docs (+ instrument profiles)."""
        if self._loaded:
            return self._count
        self._ingest_dir(CORPUS_DIR, builtin=True)
        # Operator material: the committed library plus an optional local-only
        # override dir (ATS_KNOWLEDGE_DIR). De-dup by resolved path so the same
        # folder is never ingested twice.
        seen = {CORPUS_DIR.resolve()}
        for directory in (REPO_KNOWLEDGE_DIR, Path(get_settings().knowledge_dir)):
            resolved = directory.resolve()
            if resolved in seen or not directory.exists():
                continue
            self._ingest_dir(directory, builtin=False)
            seen.add(resolved)
        if knowledge_service is not None:
            self._ingest_profiles(knowledge_service)
        self._loaded = True
        log.info("knowledge_base_loaded", extra={"chunks": self._count})
        return self._count

    def _ingest_dir(self, directory: Path, builtin: bool) -> None:
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.md")) + sorted(directory.glob("*.txt")):
            if path.name.lower() == "readme.md":  # folder docs, not knowledge
                continue
            try:
                raw = path.read_text(encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                log.warning("kb_file_error", extra={"file": path.name, "error": str(exc)})
                continue
            meta, text = _parse_front_matter(raw)
            family = _normalize_family(meta.get("family")) or _family_for(path.stem)
            default_rel = _RELIABILITY_BUILTIN if builtin else _RELIABILITY_USER
            reliability = _coerce_reliability(meta.get("reliability"), default_rel)
            source = str(meta.get("source") or path.stem)
            tickers = _coerce_tickers(meta.get("tickers"))
            base_meta = {
                "kind": "kb",
                "family": family,
                "source": source,
                "builtin": builtin,
                "reliability": reliability,
            }
            for opt in ("date", "doc_type", "url"):
                val = meta.get(opt)
                if val:
                    base_meta[opt] = str(val)
            for i, (heading, body) in enumerate(_chunk(text)):
                chunk_meta = dict(base_meta)
                chunk_meta["title"] = heading
                if tickers:
                    chunk_meta["tickers"] = tickers
                self.store.add(
                    f"kb:{path.stem}:{i}",
                    f"{heading}\n{body}" if heading else body,
                    chunk_meta,
                )
                self._count += 1

    def _ingest_profiles(self, knowledge_service: object) -> None:
        getter = getattr(knowledge_service, "all_profiles", None)
        profiles = getter() if callable(getter) else None
        if not isinstance(profiles, dict):
            return
        for symbol, prof in profiles.items():
            text = _profile_to_text(symbol, prof)
            if text:
                self.store.add(
                    f"kb:profile:{symbol}",
                    text,
                    {
                        "kind": "kb",
                        "family": "C",
                        "source": "profiles",
                        "title": symbol,
                        "tickers": [symbol],
                        "reliability": _RELIABILITY_PROFILE,
                    },
                )
                self._count += 1

    def retrieve(self, query: str, family: str | None = None, k: int = 4) -> list[dict]:
        """Top-k knowledge chunks for a query, scoped to ``family`` + shared."""
        if not query.strip():
            return []
        # Over-fetch then filter by family membership (the store's `where` does
        # exact-match only, so we can't express "family in {fam, all}" there).
        hits = self.store.search(query, k=max(k * 4, 12), where={"kind": "kb"})
        allowed = {family, "all"} if family else None
        out = []
        for h in hits:
            fam = h["metadata"].get("family")
            if allowed is not None and fam not in allowed:
                continue
            out.append(h)
            if len(out) >= k:
                break
        return out

    def __len__(self) -> int:
        return self._count


def _profile_to_text(symbol: str, prof: dict) -> str:
    if not isinstance(prof, dict):
        return ""
    if prof.get("text"):
        return f"{symbol}: {prof['text']}"
    parts = [f"{symbol} instrument profile."]
    for key in ("name", "instrument_type", "sector", "themes", "description"):
        val = prof.get(key)
        if val:
            parts.append(f"{key}: {val}")
    return " ".join(str(p) for p in parts) if len(parts) > 1 else ""


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


_WORD_RE = re.compile(r"[A-Za-z]{3,}")


def keywords(text: str, limit: int = 12) -> str:
    """Compact a blob into a keyword query (helps the BoW retriever)."""
    seen: list[str] = []
    for w in _WORD_RE.findall(text.lower()):
        if w not in seen:
            seen.append(w)
        if len(seen) >= limit:
            break
    return " ".join(seen)
