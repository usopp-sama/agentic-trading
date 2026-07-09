"""Interactive expert API.

Read + reason endpoints backing the expert console UI. These let the operator
talk to a single SME or the CIO, hand it new information, and read the
conversation history. No endpoint here can place an order or change risk state —
experts only suggest and explain.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/experts", tags=["experts"])

_SYMBOL_MAX = 32
_MESSAGE_MAX = 4000
_INFO_MAX = 8000


class AskBody(BaseModel):
    message: str = Field(min_length=1, max_length=_MESSAGE_MAX)
    symbol: str | None = Field(default=None, max_length=_SYMBOL_MAX)
    thread_id: int | None = Field(default=None, ge=1)
    info: str | None = Field(default=None, max_length=_INFO_MAX)


class RevisitBody(BaseModel):
    symbol: str = Field(min_length=1, max_length=_SYMBOL_MAX)
    info: str | None = Field(default=None, max_length=_INFO_MAX)


class DebateBody(BaseModel):
    symbol: str = Field(min_length=1, max_length=_SYMBOL_MAX)
    rounds: int | None = Field(default=None, ge=0, le=4)


class DirectiveBody(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    rule: str = Field(min_length=1, max_length=_INFO_MAX)
    symbol: str | None = Field(default=None, max_length=_SYMBOL_MAX)
    family: str | None = Field(default=None, max_length=8)
    level: str = Field(default="L2", max_length=4)
    expert: str = Field(default="human", max_length=64)


def _agents(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    agents = orch.get("agents") if orch else None
    if agents is None:
        raise HTTPException(status_code=503, detail="agent service unavailable")
    return agents


def _console(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    agents = orch.get("agents") if orch else None
    console = agents.console() if agents else None
    if console is None:
        raise HTTPException(status_code=503, detail="expert console unavailable")
    return console


@router.get("")
def list_experts(request: Request) -> dict:
    return {"experts": _console(request).experts()}


@router.post("/{expert_id}/ask")
def ask_expert(expert_id: str, body: AskBody, request: Request) -> dict:
    if not expert_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid expert id")
    symbol = body.symbol.strip().upper() if body.symbol else None
    result = _console(request).ask(
        expert_id=expert_id,
        message=body.message,
        symbol=symbol,
        thread_id=body.thread_id,
        info=body.info,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/threads")
def list_threads(request: Request, expert: str | None = None) -> dict:
    return {"threads": _console(request).list_threads(expert)}


@router.get("/threads/{thread_id}")
def get_thread(thread_id: int, request: Request) -> dict:
    thread = _console(request).get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")
    return thread


@router.post("/{expert_id}/revisit")
def revisit(expert_id: str, body: RevisitBody, request: Request) -> dict:
    if not expert_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid expert id")
    result = _console(request).revisit(expert_id, body.symbol.strip().upper(), body.info, author="human")
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/theses")
def list_theses(request: Request, expert: str | None = None, symbol: str | None = None) -> dict:
    return {"theses": _console(request).theses(expert, symbol)}


@router.get("/theses/{thesis_id}")
def thesis_history(thesis_id: int, request: Request) -> dict:
    history = _console(request).thesis_history(thesis_id)
    if not history:
        raise HTTPException(status_code=404, detail="thesis not found")
    return history


@router.post("/debate")
async def debate(body: DebateBody, request: Request) -> dict:
    return await _agents(request).debate(body.symbol.strip().upper(), body.rounds)


@router.get("/directives")
def list_directives(request: Request, symbol: str | None = None, family: str | None = None) -> dict:
    sym = symbol.strip().upper() if symbol else None
    return {"directives": _console(request).list_directives(sym, family)}


@router.post("/directives")
def add_directive(body: DirectiveBody, request: Request) -> dict:
    sym = body.symbol.strip().upper() if body.symbol else None
    return _console(request).add_directive(
        title=body.title, rule=body.rule, symbol=sym, family=body.family, level=body.level, expert=body.expert
    )


@router.delete("/directives/{stable_id}")
def forget_directive(stable_id: str, request: Request) -> dict:
    ok = _console(request).forget_directive(stable_id)
    if not ok:
        raise HTTPException(status_code=404, detail="directive not found")
    return {"forgotten": stable_id}
