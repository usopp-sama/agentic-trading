"""Self-evolving knowledge directives (SMX-style, context-only).

A directive is a small, durable, expert-authored rule — the highest-signal
knowledge an expert can hold (e.g. "For OMCs, treat a crude spike >5% as a
margin headwind", "Avoid mean-reversion on this name during results week").
Experts learn them via natural language ("remember/learn/forget"); they are
persisted, indexed into the vector store at reliability 100 (so they outrank
generic prose), and retrieved into future reasoning.

SAFETY — context only: directives inform an expert's *reasoning*. They NEVER
change risk limits, sizing, or order flow. Anything that alters trading
behaviour must go through the ``Rule`` engine (immutable guardrails + human
approval). This module deliberately has no write path into execution or risk.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import KnowledgeDirective
from ats.services.nlp.vectorstore import InMemoryVectorStore, get_vector_store

log = get_logger("ats.directives")

_DIRECTIVE_RELIABILITY = 100
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _slug(text: str, limit: int = 40) -> str:
    s = _SLUG_RE.sub("_", text.lower()).strip("_")
    return s[:limit] or "note"


def _doc_id(stable_id: str) -> str:
    return f"directive:{stable_id}"


class DirectiveStore:
    def __init__(self, store: InMemoryVectorStore | None = None) -> None:
        self.store = store or get_vector_store()

    # --- lifecycle ---------------------------------------------------------
    def load_all(self) -> int:
        """Index every active directive into the vector store (startup)."""
        n = 0
        with session_scope() as s:
            rows = s.execute(
                select(KnowledgeDirective).where(KnowledgeDirective.status == "active")
            ).scalars().all()
            for r in rows:
                self._index(r)
                n += 1
        log.info("directives_loaded", extra={"count": n})
        return n

    # --- CRUD --------------------------------------------------------------
    def upsert(
        self,
        title: str,
        rule: str,
        *,
        expert: str = "human",
        author: str = "human",
        scope: str = "global",
        symbol: str | None = None,
        family: str | None = None,
        level: str = "L2",
        category: str = "operational",
        stable_id: str | None = None,
        source_thread: int | None = None,
    ) -> dict:
        symbol = symbol.strip().upper() if symbol else None
        if symbol and scope == "global":
            scope = "symbol"
        sid = stable_id or self._make_stable_id(scope, symbol, title)
        with session_scope() as s:
            row = s.execute(
                select(KnowledgeDirective).where(KnowledgeDirective.stable_id == sid)
            ).scalar_one_or_none()
            created = row is None
            if row is None:
                row = KnowledgeDirective(stable_id=sid)
                s.add(row)
            row.expert = expert
            row.author = author
            row.scope = scope
            row.symbol = symbol
            row.family = family
            row.level = level
            row.title = title.strip()[:256]
            row.rule = rule.strip()
            row.category = category
            row.reliability = _DIRECTIVE_RELIABILITY
            row.status = "active"
            row.source_thread = source_thread
            row.updated_ts = _utcnow()
            s.flush()
            self._index(row)
            result = self._to_dict(row) | {"created": created}
        return result

    def forget(self, stable_id: str) -> bool:
        with session_scope() as s:
            row = s.execute(
                select(KnowledgeDirective).where(KnowledgeDirective.stable_id == stable_id)
            ).scalar_one_or_none()
            if row is None:
                return False
            row.status = "retired"
            row.updated_ts = _utcnow()
        self.store.delete(_doc_id(stable_id))
        return True

    def forget_match(self, query: str, symbol: str | None = None) -> dict | None:
        """Retire the directive most relevant to a free-text 'forget X'."""
        hits = self.retrieve(query, symbol=symbol, k=1)
        if not hits:
            return None
        sid = hits[0]["stable_id"]
        return hits[0] if self.forget(sid) else None

    # --- retrieval ---------------------------------------------------------
    def retrieve(self, query: str, symbol: str | None = None, family: str | None = None, k: int = 4) -> list[dict]:
        symbol = symbol.strip().upper() if symbol else None
        out: list[dict] = []
        seen: set[str] = set()

        def _accept(m: dict, text: str, score: float) -> None:
            sid = m.get("stable_id")
            if sid in seen:
                return
            seen.add(sid)
            out.append({
                "stable_id": sid, "title": m.get("title"), "text": text,
                "scope": m.get("scope"), "symbol": m.get("symbol"),
                "level": m.get("level"), "score": score,
            })

        # 1) Pinned: every active directive explicitly scoped to this symbol is
        #    relevant by construction (not gated on fuzzy text match).
        if symbol:
            for d in self.list_directives(symbol=symbol):
                if d.get("family") and family and d["family"] != family:
                    continue
                _accept({"stable_id": d["stable_id"], "title": d["title"], "symbol": d["symbol"],
                         "scope": d["scope"], "level": d["level"]}, f"{d['title']}\n{d['rule']}", 1.0)

        # 2) Relevance: global / family directives matched by hybrid search.
        for h in self.store.search(query or symbol or "", k=max(k * 4, 12), where={"kind": "directive"}):
            m = h["metadata"]
            d_symbol = m.get("symbol")
            if d_symbol:  # symbol-scoped handled above; skip other symbols here
                continue
            if m.get("family") and family and m["family"] != family:
                continue
            _accept(m, h["text"], h["score"])
            if len(out) >= k + 4:
                break
        return out[:k]

    def list_directives(self, symbol: str | None = None, family: str | None = None, status: str = "active") -> list[dict]:
        with session_scope() as s:
            stmt = select(KnowledgeDirective).where(KnowledgeDirective.status == status)
            if symbol:
                stmt = stmt.where(KnowledgeDirective.symbol == symbol.strip().upper())
            if family:
                stmt = stmt.where(KnowledgeDirective.family == family)
            rows = s.execute(stmt.order_by(KnowledgeDirective.updated_ts.desc()).limit(300)).scalars().all()
            return [self._to_dict(r) for r in rows]

    # --- internals ---------------------------------------------------------
    def _index(self, row: KnowledgeDirective) -> None:
        self.store.add(
            _doc_id(row.stable_id),
            f"{row.title}\n{row.rule}",
            {
                "kind": "directive",
                "stable_id": row.stable_id,
                "title": row.title,
                "symbol": row.symbol,
                "family": row.family,
                "scope": row.scope,
                "level": row.level,
                "reliability": row.reliability,
            },
        )

    def _make_stable_id(self, scope: str, symbol: str | None, title: str) -> str:
        prefix = (symbol.lower() if symbol else scope)
        base = f"{prefix}.{_slug(title)}"
        # de-dupe suffix if needed
        sid = base
        i = 1
        with session_scope() as s:
            while s.execute(
                select(KnowledgeDirective.id).where(KnowledgeDirective.stable_id == sid)
            ).scalar_one_or_none() is not None:
                i += 1
                sid = f"{base}_{i}"
        return sid

    @staticmethod
    def _to_dict(row: KnowledgeDirective) -> dict:
        return {
            "stable_id": row.stable_id,
            "expert": row.expert,
            "author": row.author,
            "scope": row.scope,
            "symbol": row.symbol,
            "family": row.family,
            "level": row.level,
            "title": row.title,
            "rule": row.rule,
            "category": row.category,
            "status": row.status,
            "updated_ts": row.updated_ts.isoformat() if row.updated_ts else None,
        }


_directives: DirectiveStore | None = None


def get_directive_store() -> DirectiveStore:
    global _directives
    if _directives is None:
        _directives = DirectiveStore()
    return _directives
