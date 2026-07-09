"""Research factory API: the hypothesis registry + committee approval flow.

Read endpoints back the /research page; write endpoints are the human's
levers (propose, advance, approve/reject recommendations, trigger a role
run). Everything a research agent does autonomously goes through the same
registry functions, so the audit trail is identical either way.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Request
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.models import AllocationRecommendation, ResearchNote
from ats.services.research import hypotheses as registry
from ats.services.research.hypotheses import RegistryError

router = APIRouter(prefix="/api/research", tags=["research"])


def _factory(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    return orch.get("research") if orch else None


@router.get("")
def research_overview(request: Request) -> dict:
    """Everything the /research page needs in one call."""
    factory = _factory(request)
    with session_scope() as s:
        recs = s.execute(
            select(AllocationRecommendation)
            .order_by(AllocationRecommendation.id.desc()).limit(12)
        ).scalars().all()
        notes = s.execute(
            select(ResearchNote).order_by(ResearchNote.id.desc()).limit(30)
        ).scalars().all()
        rec_rows = [
            {
                "id": r.id, "ts": r.ts.isoformat() if r.ts else "",
                "summary": r.summary, "rationale": r.rationale,
                "tilts": r.tilts or {}, "status": r.status, "actor": r.actor,
            }
            for r in recs
        ]
        note_rows = [
            {
                "id": n.id, "ts": n.ts.isoformat() if n.ts else "",
                "role": n.role, "title": n.title,
                "content": n.content, "meta": n.meta or {},
            }
            for n in notes
        ]
    return {
        "stages": list(registry.STAGES),
        "kanban": registry.by_stage(),
        "scores": registry.survival_scores(),
        "recommendations": rec_rows,
        "notes": note_rows,
        "factory": factory.status() if factory else {"enabled": False},
    }


@router.get("/hypotheses/{hyp_id}")
def hypothesis_detail(hyp_id: int) -> dict:
    try:
        return registry.get(hyp_id)
    except RegistryError as exc:
        return {"error": str(exc)}


@router.post("/hypotheses")
def propose_hypothesis(
    title: str = Body(embed=True),
    thesis: str = Body(embed=True, default=""),
    evidence: str = Body(embed=True, default=""),
    rule: str = Body(embed=True, default=""),
) -> dict:
    """Manual proposal from the dashboard — credited to the human."""
    try:
        h = registry.propose(agent="human", title=title, thesis=thesis,
                             evidence=evidence)
        if rule.strip():
            h = registry.specify(h["id"], rule=rule, actor="human")
        return h
    except RegistryError as exc:
        return {"error": str(exc)}


@router.post("/hypotheses/{hyp_id}/advance")
def advance_hypothesis(
    hyp_id: int,
    to_stage: str = Body(embed=True),
    note: str = Body(embed=True, default=""),
    rule: str = Body(embed=True, default=""),
) -> dict:
    """Move a hypothesis along its lifecycle (human action from the page)."""
    try:
        if to_stage.upper() == "SPECIFIED":
            return registry.specify(hyp_id, rule=rule, actor="human")
        return registry.advance(hyp_id, to_stage, actor="human", note=note)
    except RegistryError as exc:
        return {"error": str(exc)}


@router.post("/run/{role}")
def run_role(role: str, request: Request) -> dict:
    """Manual trigger for one research role (you clicked, you pay)."""
    factory = _factory(request)
    if factory is None:
        return {"error": "research factory not running"}
    return factory.run_role(role, actor="human")


@router.post("/recommendations/{rec_id}/approve")
def approve_recommendation(rec_id: int, request: Request) -> dict:
    factory = _factory(request)
    if factory is None:
        return {"error": "research factory not running"}
    return factory.approve_recommendation(rec_id, actor="human")


@router.post("/recommendations/{rec_id}/reject")
def reject_recommendation(rec_id: int, request: Request) -> dict:
    factory = _factory(request)
    if factory is None:
        return {"error": "research factory not running"}
    return factory.reject_recommendation(rec_id, actor="human")
