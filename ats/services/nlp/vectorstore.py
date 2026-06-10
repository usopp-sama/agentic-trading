"""Vector store for RAG.

Default is a dependency-free in-memory store using a hashing bag-of-words
embedding with cosine similarity - good enough for retrieving relevant recent
news/profiles offline. If ``chromadb`` + ``sentence-transformers`` are present
and ``ATS_VECTOR_STORE=chroma``, a richer backend can be swapped in later.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

_DIM = 512
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _embed(text: str) -> dict[int, float]:
    """Sparse hashed bag-of-words vector (token -> weight)."""
    counts: dict[int, float] = defaultdict(float)
    for tok in _TOKEN_RE.findall(text.lower()):
        if len(tok) < 3:
            continue
        counts[hash(tok) % _DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def _cosine(a: dict[int, float], b: dict[int, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


@dataclass
class _Doc:
    doc_id: str
    text: str
    metadata: dict
    vector: dict[int, float] = field(default_factory=dict)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._docs: dict[str, _Doc] = {}

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        self._docs[doc_id] = _Doc(doc_id, text, metadata or {}, _embed(text))

    def search(self, query: str, k: int = 5, where: dict | None = None) -> list[dict]:
        q = _embed(query)
        scored = []
        for doc in self._docs.values():
            if where and not all(doc.metadata.get(kk) == vv for kk, vv in where.items()):
                continue
            scored.append((_cosine(q, doc.vector), doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"doc_id": d.doc_id, "text": d.text, "score": round(s, 4), "metadata": d.metadata}
            for s, d in scored[:k]
            if s > 0
        ]

    def search_symbol(self, symbol: str, k: int = 5) -> list[dict]:
        out = []
        for doc in self._docs.values():
            if symbol in (doc.metadata.get("tickers") or []):
                out.append(
                    {"doc_id": doc.doc_id, "text": doc.text, "score": 1.0, "metadata": doc.metadata}
                )
        return out[-k:]

    def __len__(self) -> int:
        return len(self._docs)


_store: InMemoryVectorStore | None = None


def get_vector_store() -> InMemoryVectorStore:
    global _store
    if _store is None:
        _store = InMemoryVectorStore()
    return _store
