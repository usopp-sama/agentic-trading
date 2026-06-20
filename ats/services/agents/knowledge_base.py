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
"""

from __future__ import annotations

import re
from pathlib import Path

from ats.core.config import get_settings
from ats.core.logging import get_logger
from ats.services.nlp.vectorstore import InMemoryVectorStore, get_vector_store

log = get_logger("ats.knowledge_base")

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

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
        user_dir = Path(get_settings().knowledge_dir)
        if user_dir.exists():
            self._ingest_dir(user_dir, builtin=False)
        if knowledge_service is not None:
            self._ingest_profiles(knowledge_service)
        self._loaded = True
        log.info("knowledge_base_loaded", extra={"chunks": self._count})
        return self._count

    def _ingest_dir(self, directory: Path, builtin: bool) -> None:
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.md")) + sorted(directory.glob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                log.warning("kb_file_error", extra={"file": path.name, "error": str(exc)})
                continue
            family = _family_for(path.stem)
            reliability = _RELIABILITY_BUILTIN if builtin else _RELIABILITY_USER
            for i, (heading, body) in enumerate(_chunk(text)):
                doc_id = f"kb:{path.stem}:{i}"
                self.store.add(
                    doc_id,
                    f"{heading}\n{body}" if heading else body,
                    {
                        "kind": "kb",
                        "family": family,
                        "source": path.stem,
                        "title": heading,
                        "builtin": builtin,
                        "reliability": reliability,
                    },
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
