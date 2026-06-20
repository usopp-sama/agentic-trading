"""Vector store for RAG (hybrid retrieval, dependency-free).

Default is an in-memory store that fuses two signals, mirroring the proven
SMX/MDRAG design:

- **Semantic** — a hashing bag-of-words vector with cosine similarity.
- **Keyword** — a pure-python BM25 score over the same tokens.

The two are normalized and blended (``alpha`` favours semantic), then scaled by
each source's **reliability** (0-100) so authoritative material (directives,
filings) outranks chatter. This needs no extra dependencies and runs offline.
If ``chromadb`` + ``sentence-transformers`` are present and
``ATS_VECTOR_STORE=chroma``, a richer backend can be swapped in behind the same
interface later.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

_DIM = 512
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Hybrid fusion + BM25 parameters (SMX defaults: alpha=0.7).
_ALPHA = 0.7
_BM25_K1 = 1.5
_BM25_B = 0.75


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) >= 3]


def _embed(text: str) -> dict[int, float]:
    """Sparse hashed bag-of-words vector (token -> normalized weight)."""
    counts: dict[int, float] = defaultdict(float)
    for tok in _tokens(text):
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
    tokens: list[str] = field(default_factory=list)
    tf: Counter = field(default_factory=Counter)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._docs: dict[str, _Doc] = {}

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        toks = _tokens(text)
        self._docs[doc_id] = _Doc(doc_id, text, metadata or {}, _embed(text), toks, Counter(toks))

    def delete(self, doc_id: str) -> bool:
        return self._docs.pop(doc_id, None) is not None

    def search(self, query: str, k: int = 5, where: dict | None = None, alpha: float = _ALPHA) -> list[dict]:
        candidates = [
            d for d in self._docs.values()
            if not where or all(d.metadata.get(kk) == vv for kk, vv in where.items())
        ]
        if not candidates or not query.strip():
            return []

        q_vec = _embed(query)
        q_tokens = _tokens(query)
        cos = {d.doc_id: _cosine(q_vec, d.vector) for d in candidates}
        bm = self._bm25(q_tokens, candidates)
        cos_max = max(cos.values()) or 1.0
        bm_max = max(bm.values()) or 1.0

        scored: list[tuple[float, float, float, _Doc]] = []
        for d in candidates:
            c = cos[d.doc_id] / cos_max if cos_max > 0 else 0.0
            b = bm[d.doc_id] / bm_max if bm_max > 0 else 0.0
            fused = alpha * c + (1.0 - alpha) * b
            reliability = float(d.metadata.get("reliability", 100)) / 100.0
            scored.append((fused * reliability, c, b, d))
        scored.sort(key=lambda x: x[0], reverse=True)

        out: list[dict] = []
        for score, c, b, d in scored[:k]:
            if score <= 0:
                continue
            out.append(
                {
                    "doc_id": d.doc_id,
                    "text": d.text,
                    "score": round(score, 4),
                    "scores": {"cosine": round(c, 4), "bm25": round(b, 4)},
                    "metadata": d.metadata,
                }
            )
        return out

    def _bm25(self, q_tokens: list[str], candidates: list[_Doc]) -> dict[str, float]:
        n = len(candidates)
        if n == 0 or not q_tokens:
            return {d.doc_id: 0.0 for d in candidates}
        df: Counter = Counter()
        for d in candidates:
            for term in d.tf:
                df[term] += 1
        avgdl = sum(len(d.tokens) for d in candidates) / n or 1.0
        scores: dict[str, float] = {}
        for d in candidates:
            dl = len(d.tokens) or 1
            s = 0.0
            for term in q_tokens:
                f = d.tf.get(term, 0)
                if not f:
                    continue
                idf = math.log(1.0 + (n - df[term] + 0.5) / (df[term] + 0.5))
                s += idf * (f * (_BM25_K1 + 1)) / (f + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / avgdl))
            scores[d.doc_id] = s
        return scores

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
