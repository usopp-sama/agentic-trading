"""Control + read API.

Control endpoints (kill switch, mode) are the human's safety levers. Read
endpoints back the dashboard. The real-money gate is config-only and cannot be
opened over the API by design.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Request

from ats.core.config import get_settings
from ats.core import state

router = APIRouter(prefix="/api", tags=["control"])


def _execution(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    return orch.get("execution") if orch else None


def _last_bar_age_s() -> float | None:
    """Seconds since the most recent stored OHLCV bar (None if no data)."""
    from datetime import datetime, timezone

    from sqlalchemy import func, select

    from ats.core.db import session_scope
    from ats.core.models import Ohlcv

    try:
        with session_scope() as s:
            last = s.execute(select(func.max(Ohlcv.ts))).scalar_one_or_none()
        if last is None:
            return None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return round((now - last).total_seconds(), 1)
    except Exception:  # noqa: BLE001
        return None


@router.get("/health")
def health(request: Request) -> dict:
    """Rich liveness/readiness probe for an unattended run.

    Reports DB reachability, orchestrator status, the live-vs-synthetic feed
    ratio, last-bar age, the kill switch, and whether SME reasoning is really
    live. ``status`` is ``degraded`` if anything material is wrong so a simple
    cron/uptime check can alert.
    """
    out: dict = {"status": "ok", "version": "0.1.0"}
    orch = getattr(request.app.state, "orchestrator", None)

    # DB ping
    db_ok = True
    try:
        from sqlalchemy import text

        from ats.core.db import session_scope

        with session_scope() as s:
            s.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    out["db_ok"] = db_ok

    out["kill_switch"] = state.is_killed()
    out["mode"] = state.get_mode()
    out["last_bar_age_s"] = _last_bar_age_s()

    if orch is not None:
        out["orchestrator"] = {
            "started": bool(getattr(orch, "_started", False)),
            "services": len(getattr(orch, "services", [])),
        }
        md = orch.get("market_data")
        if md is not None and hasattr(md, "data_status"):
            out["feed"] = md.data_status()
        agents = orch.get("agents")
        if agents is not None and hasattr(agents, "llm_status"):
            out["llm"] = agents.llm_status()
        wd = orch.get("watchdog")
        if wd is not None and hasattr(wd, "status"):
            out["watchdog"] = wd.status()

    feed_degraded = bool(out.get("feed", {}).get("degraded"))
    if (not db_ok) or out["kill_switch"] or feed_degraded:
        out["status"] = "degraded"
    return out


@router.get("/state")
def get_state() -> dict:
    settings = get_settings()
    return {
        "mode": state.get_mode(),
        "kill_switch": state.is_killed(),
        "real_money_enabled": settings.real_money_enabled,
        "real_money_active": state.real_money_active(),
        "base_currency": settings.base_currency,
        "data_source": settings.data_source,
        "llm_provider": settings.llm_provider,
        "audit_chain_ok": state.verify_audit_chain(),
    }


@router.post("/kill")
def kill(engage: bool = Body(embed=True, default=True), reason: str = Body(embed=True, default="manual")) -> dict:
    if engage:
        state.engage_kill_switch(actor="human", reason=reason)
    else:
        state.release_kill_switch(actor="human")
    return {"kill_switch": state.is_killed()}


@router.post("/mode")
def set_mode(mode: str = Body(embed=True)) -> dict:
    new_mode = state.set_mode(mode, actor="human")
    return {"mode": new_mode}


@router.get("/approvals")
def list_approvals(request: Request) -> dict:
    ex = _execution(request)
    return {"pending": ex.list_pending_approvals() if ex else []}


@router.post("/approvals/{decision_id}/approve")
async def approve(decision_id: int, request: Request) -> dict:
    ex = _execution(request)
    if not ex:
        return {"status": "unavailable"}
    return await ex.approve_decision(decision_id, actor="human")


@router.post("/approvals/{decision_id}/reject")
def reject(decision_id: int, request: Request) -> dict:
    ex = _execution(request)
    if not ex:
        return {"status": "unavailable"}
    return ex.reject_decision(decision_id, actor="human")
