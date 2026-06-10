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


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


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
