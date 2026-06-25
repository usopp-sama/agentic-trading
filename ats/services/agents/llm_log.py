"""LLM call recorder.

Captures every *real* provider call (the question sent to the model and its
answer) for the dashboard's LLM history. Each call is appended to an in-memory
ring (instant, survives DB hiccups) and persisted to the ``llm_calls`` table
(survives restarts). Old rows are trimmed so the SQLite file stays bounded.

Recording is strictly best-effort: it must never break or slow an LLM call, so
every persistence path swallows its own errors.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone

from ats.core.logging import get_logger

log = get_logger("ats.llm_log")

# Cap what we store per row so a giant RAG context can't bloat the DB.
_MAX_PROMPT = 16_000
_MAX_RESPONSE = 16_000
# Keep at most this many rows; trim occasionally (not every insert).
_MAX_ROWS = 5_000
_TRIM_EVERY = 200

_RING: deque[dict] = deque(maxlen=500)
_RING_LOCK = threading.Lock()
_since_trim = 0
_TRIM_LOCK = threading.Lock()

# Published Gemini paid-tier rates (USD per 1M tokens): (input, output).
# Source: ai.google.dev/gemini-api/docs/pricing. Used only for a *local*
# cost estimate from recorded tokens — Google's billing dashboard is
# authoritative (caching, free-tier allowances, and rounding differ).
_RATES_USD_PER_M: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
}
_DEFAULT_RATE = (0.30, 2.50)
# Display-only FX; override via ATS_USD_INR if you want a different rate.
_USD_INR_FALLBACK = 86.0


def _usd_inr() -> float:
    import os

    try:
        return float(os.environ.get("ATS_USD_INR", "") or _USD_INR_FALLBACK)
    except ValueError:
        return _USD_INR_FALLBACK


def _est_cost_usd(model: str, in_tok: int, out_tok: int) -> float:
    rin, rout = _RATES_USD_PER_M.get(model, _DEFAULT_RATE)
    return (in_tok / 1_000_000) * rin + (out_tok / 1_000_000) * rout


def record_llm_call(
    *,
    kind: str,
    provider: str,
    model: str,
    persona: str = "",
    symbol: str = "",
    prompt: str = "",
    response: str = "",
    latency_ms: int = 0,
    ok: bool = True,
    error: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "provider": provider,
        "model": model,
        "persona": persona or "",
        "symbol": symbol or "",
        "prompt": (prompt or "")[:_MAX_PROMPT],
        "response": (response or "")[:_MAX_RESPONSE],
        "latency_ms": int(latency_ms),
        "ok": bool(ok),
        "error": (error or "")[:1000],
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
    }
    with _RING_LOCK:
        _RING.appendleft(rec)
    _persist(rec)


def _persist(rec: dict) -> None:
    global _since_trim
    try:
        from ats.core.db import session_scope
        from ats.core.models import LlmCall

        with session_scope() as s:
            s.add(LlmCall(
                kind=rec["kind"], provider=rec["provider"], model=rec["model"],
                persona=rec["persona"], symbol=rec["symbol"], prompt=rec["prompt"],
                response=rec["response"], latency_ms=rec["latency_ms"], ok=rec["ok"],
                error=rec["error"], prompt_tokens=rec["prompt_tokens"],
                completion_tokens=rec["completion_tokens"],
            ))
    except Exception as exc:  # noqa: BLE001 - recording must never break a call
        log.debug("llm_call_persist_failed", extra={"error": str(exc)})
        return

    with _TRIM_LOCK:
        _since_trim += 1
        due = _since_trim >= _TRIM_EVERY
        if due:
            _since_trim = 0
    if due:
        _trim()


def _trim() -> None:
    """Delete all but the most recent ``_MAX_ROWS`` rows."""
    try:
        from sqlalchemy import select

        from ats.core.db import session_scope
        from ats.core.models import LlmCall

        with session_scope() as s:
            cutoff = s.execute(
                select(LlmCall.id).order_by(LlmCall.id.desc()).offset(_MAX_ROWS).limit(1)
            ).scalar()
            if cutoff:
                s.query(LlmCall).filter(LlmCall.id <= cutoff).delete(synchronize_session=False)
    except Exception as exc:  # noqa: BLE001
        log.debug("llm_call_trim_failed", extra={"error": str(exc)})


def recent_calls(limit: int = 100, kind: str | None = None, ok: bool | None = None) -> list[dict]:
    """Most recent calls, newest first. Reads the DB (survives restarts) and
    falls back to the in-memory ring if the DB is unavailable."""
    limit = max(1, min(limit, 500))
    try:
        from sqlalchemy import select

        from ats.core.db import session_scope
        from ats.core.models import LlmCall

        with session_scope() as s:
            q = select(LlmCall).order_by(LlmCall.id.desc())
            if kind:
                q = q.where(LlmCall.kind == kind)
            if ok is not None:
                q = q.where(LlmCall.ok == ok)
            rows = s.execute(q.limit(limit)).scalars().all()
            return [_row_to_dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        log.debug("llm_calls_read_failed", extra={"error": str(exc)})
        with _RING_LOCK:
            items = list(_RING)
        if kind:
            items = [r for r in items if r.get("kind") == kind]
        if ok is not None:
            items = [r for r in items if r.get("ok") == ok]
        return items[:limit]


def usage_summary(days: int | None = None) -> dict:
    """Token + estimated-cost rollup from recorded calls, grouped by model.

    Only successful (billed) calls contribute tokens/cost; failed calls are
    counted separately. This is an *estimate* from per-response token counts —
    Google's billing console is the source of truth. ``days`` limits the window.
    """
    try:
        from datetime import timedelta

        from sqlalchemy import func, select

        from ats.core.db import session_scope
        from ats.core.models import LlmCall

        with session_scope() as s:
            base = select(
                LlmCall.model,
                func.count(),
                func.sum(LlmCall.prompt_tokens),
                func.sum(LlmCall.completion_tokens),
            ).where(LlmCall.ok.is_(True)).group_by(LlmCall.model)
            fail_q = select(func.count()).select_from(LlmCall).where(LlmCall.ok.is_(False))
            span_q = select(func.min(LlmCall.ts), func.max(LlmCall.ts))
            if days:
                cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
                base = base.where(LlmCall.ts >= cutoff)
                fail_q = fail_q.where(LlmCall.ts >= cutoff)
                span_q = span_q.where(LlmCall.ts >= cutoff)

            rows = s.execute(base).all()
            failed = int(s.execute(fail_q).scalar() or 0)
            span = s.execute(span_q).first()

        per_model = []
        tot_in = tot_out = tot_calls = 0
        tot_usd = 0.0
        for model, cnt, pin, pout in rows:
            pin = int(pin or 0)
            pout = int(pout or 0)
            usd = _est_cost_usd(model or "", pin, pout)
            per_model.append({
                "model": model or "?", "calls": int(cnt),
                "input_tokens": pin, "output_tokens": pout,
                "est_usd": round(usd, 4),
            })
            tot_in += pin
            tot_out += pout
            tot_calls += int(cnt)
            tot_usd += usd

        fx = _usd_inr()
        per_model.sort(key=lambda r: -r["est_usd"])
        return {
            "since": span[0].replace(tzinfo=timezone.utc).isoformat() if span and span[0] else "",
            "until": span[1].replace(tzinfo=timezone.utc).isoformat() if span and span[1] else "",
            "by_model": per_model,
            "ok_calls": tot_calls,
            "failed_calls": failed,
            "input_tokens": tot_in,
            "output_tokens": tot_out,
            "est_usd": round(tot_usd, 4),
            "est_inr": round(tot_usd * fx, 2),
            "usd_inr": fx,
            "note": "Estimate from recorded tokens since the recorder was enabled; "
                    "Google's billing console is authoritative.",
        }
    except Exception as exc:  # noqa: BLE001
        log.debug("llm_usage_summary_failed", extra={"error": str(exc)})
        return {"by_model": [], "ok_calls": 0, "failed_calls": 0, "est_usd": 0.0,
                "est_inr": 0.0, "note": "usage unavailable"}


def _row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "ts": r.ts.replace(tzinfo=timezone.utc).isoformat() if r.ts else "",
        "kind": r.kind,
        "provider": r.provider,
        "model": r.model,
        "persona": r.persona,
        "symbol": r.symbol,
        "prompt": r.prompt,
        "response": r.response,
        "latency_ms": r.latency_ms,
        "ok": r.ok,
        "error": r.error,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
    }
