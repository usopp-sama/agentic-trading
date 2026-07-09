"""Hypothesis registry: the backbone of the slow loop (plan §3.1).

Pure persistence + lifecycle rules; no LLM, no scheduling. The research
factory and the dashboard both talk to the registry through this module.

Lifecycle (one direction, REJECTED reachable from anywhere active):

    PROPOSED → SPECIFIED → BACKTESTED → SHADOW → PAPER → LIVE
        └──────────┴───────────┴──────────┴────────┴──→ REJECTED

Every transition writes a ``HypothesisEvent`` row (who, when, why), so a
hypothesis's whole history is auditable. Agents are scored by survival:
of their decided hypotheses (survived to SHADOW+ or rejected), what
fraction survived. That replaces per-trade attribution — meaningless at
our trade counts — as the primary agent metric.
"""

from __future__ import annotations

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Hypothesis, HypothesisEvent

log = get_logger("ats.research.hypotheses")

STAGES = ("PROPOSED", "SPECIFIED", "BACKTESTED", "SHADOW", "PAPER", "LIVE", "REJECTED")
_ACTIVE = ("PROPOSED", "SPECIFIED", "BACKTESTED", "SHADOW", "PAPER", "LIVE")
SURVIVING = ("SHADOW", "PAPER", "LIVE")

_TRANSITIONS: dict[str, set[str]] = {
    "PROPOSED": {"SPECIFIED", "REJECTED"},
    "SPECIFIED": {"BACKTESTED", "REJECTED"},
    "BACKTESTED": {"SHADOW", "REJECTED"},
    "SHADOW": {"PAPER", "REJECTED"},
    "PAPER": {"LIVE", "REJECTED"},
    "LIVE": {"REJECTED"},  # retirement
    "REJECTED": set(),
}


class RegistryError(RuntimeError):
    """Illegal hypothesis operation (bad stage move, missing rule, …)."""


def can_advance(from_stage: str, to_stage: str) -> bool:
    return to_stage in _TRANSITIONS.get(from_stage, set())


def propose(
    agent: str,
    title: str,
    thesis: str = "",
    evidence: str = "",
    rule: str = "",
    params: dict | None = None,
    universe: list | None = None,
) -> dict:
    """Register a new hypothesis at PROPOSED (specify() moves it on)."""
    if not title.strip():
        raise RegistryError("hypothesis needs a title")
    if not agent.strip():
        raise RegistryError("hypothesis needs a proposing agent")
    with session_scope() as s:
        h = Hypothesis(
            title=title.strip()[:256], agent=agent.strip(),
            thesis=thesis, evidence=evidence, rule=rule,
            params=params or {}, universe=universe or [],
        )
        s.add(h)
        s.flush()
        s.add(HypothesisEvent(
            hypothesis_id=h.id, from_stage="", to_stage="PROPOSED",
            actor=agent, note="proposed",
        ))
        hid = h.id
    log.info("hypothesis_proposed", extra={"id": hid, "agent": agent, "title": title[:80]})
    return get(hid)


def specify(
    hyp_id: int, rule: str, params: dict | None = None,
    universe: list | None = None, actor: str = "system",
) -> dict:
    """Attach the exact backtestable rule → SPECIFIED."""
    if not rule.strip():
        raise RegistryError("SPECIFIED requires an exact, backtestable rule")
    with session_scope() as s:
        h = _get_row(s, hyp_id)
        _move(s, h, "SPECIFIED", actor, note="rule attached")
        h.rule = rule
        if params is not None:
            h.params = params
        if universe is not None:
            h.universe = universe
    return get(hyp_id)


def attach_backtest(hyp_id: int, result: dict, actor: str = "backtest_gate") -> dict:
    """Record the walk-forward gate result → BACKTESTED.

    ``result`` should carry at least a verdict-relevant metric set
    (sharpe/deflated_sharpe/windows); the registry stores it verbatim.
    """
    if not result:
        raise RegistryError("BACKTESTED requires a non-empty result")
    with session_scope() as s:
        h = _get_row(s, hyp_id)
        _move(s, h, "BACKTESTED", actor,
              note=f"gate result attached: {_result_line(result)}")
        h.backtest = result
    return get(hyp_id)


def advance(hyp_id: int, to_stage: str, actor: str, note: str = "") -> dict:
    """Move a hypothesis along the lifecycle (or reject it)."""
    to_stage = to_stage.upper().strip()
    if to_stage not in STAGES:
        raise RegistryError(f"unknown stage {to_stage!r}")
    with session_scope() as s:
        h = _get_row(s, hyp_id)
        if to_stage == "SPECIFIED" and not h.rule.strip():
            raise RegistryError("cannot enter SPECIFIED without a rule; use specify()")
        if to_stage == "BACKTESTED" and not h.backtest:
            raise RegistryError("cannot enter BACKTESTED without a result; use attach_backtest()")
        _move(s, h, to_stage, actor, note)
    return get(hyp_id)


def link_strategy(hyp_id: int, strategy_id: str, actor: str = "system") -> dict:
    """Record which registered sleeve implements this hypothesis."""
    with session_scope() as s:
        h = _get_row(s, hyp_id)
        h.strategy_id = strategy_id
        s.add(HypothesisEvent(
            hypothesis_id=h.id, from_stage=h.stage, to_stage=h.stage,
            actor=actor, note=f"implemented by strategy {strategy_id}",
        ))
    return get(hyp_id)


# --- reads --------------------------------------------------------------------
def get(hyp_id: int) -> dict:
    with session_scope() as s:
        h = _get_row(s, hyp_id)
        events = s.execute(
            select(HypothesisEvent)
            .where(HypothesisEvent.hypothesis_id == hyp_id)
            .order_by(HypothesisEvent.ts, HypothesisEvent.id)
        ).scalars().all()
        return {**_to_dict(h), "events": [_event_dict(e) for e in events]}


def list_all(stage: str | None = None, limit: int = 200) -> list[dict]:
    with session_scope() as s:
        q = select(Hypothesis).order_by(Hypothesis.updated_ts.desc()).limit(limit)
        if stage:
            q = q.where(Hypothesis.stage == stage.upper())
        return [_to_dict(h) for h in s.execute(q).scalars().all()]


def survival_scores() -> list[dict]:
    """Per-agent scoreboard: proposals, decided, survived, survival rate.

    A hypothesis is *decided* once it survives to SHADOW+ or is REJECTED;
    everything earlier is still in flight and scores nothing.
    """
    with session_scope() as s:
        rows = s.execute(select(Hypothesis.agent, Hypothesis.stage)).all()
    by_agent: dict[str, dict] = {}
    for agent, stage in rows:
        rec = by_agent.setdefault(
            agent, {"agent": agent, "proposed": 0, "in_flight": 0,
                    "survived": 0, "rejected": 0},
        )
        rec["proposed"] += 1
        if stage in SURVIVING:
            rec["survived"] += 1
        elif stage == "REJECTED":
            rec["rejected"] += 1
        else:
            rec["in_flight"] += 1
    out = []
    for rec in by_agent.values():
        decided = rec["survived"] + rec["rejected"]
        rec["survival_rate"] = round(rec["survived"] / decided, 3) if decided else None
        out.append(rec)
    out.sort(key=lambda r: (-(r["survival_rate"] or 0.0), -r["proposed"]))
    return out


def by_stage() -> dict[str, list[dict]]:
    """Kanban feed for the /research page."""
    out: dict[str, list[dict]] = {stage: [] for stage in STAGES}
    for h in list_all(limit=500):
        out.setdefault(h["stage"], []).append(h)
    return out


# --- internals ------------------------------------------------------------------
def _get_row(s, hyp_id: int) -> Hypothesis:
    h = s.get(Hypothesis, hyp_id)
    if h is None:
        raise RegistryError(f"unknown hypothesis {hyp_id}")
    return h


def _move(s, h: Hypothesis, to_stage: str, actor: str, note: str = "") -> None:
    if not can_advance(h.stage, to_stage):
        raise RegistryError(f"illegal stage move {h.stage} → {to_stage} (#{h.id})")
    s.add(HypothesisEvent(
        hypothesis_id=h.id, from_stage=h.stage, to_stage=to_stage,
        actor=actor, note=note[:2000],
    ))
    log.info("hypothesis_stage", extra={"id": h.id, "from": h.stage,
                                        "to": to_stage, "actor": actor})
    h.stage = to_stage


def _result_line(result: dict) -> str:
    keys = ("sharpe", "deflated_sharpe", "windows", "verdict")
    return ", ".join(f"{k}={result[k]}" for k in keys if k in result)[:160]


def _to_dict(h: Hypothesis) -> dict:
    return {
        "id": h.id,
        "created_ts": h.created_ts.isoformat() if h.created_ts else "",
        "updated_ts": h.updated_ts.isoformat() if h.updated_ts else "",
        "title": h.title,
        "agent": h.agent,
        "thesis": h.thesis,
        "evidence": h.evidence,
        "rule": h.rule,
        "params": h.params or {},
        "universe": h.universe or [],
        "stage": h.stage,
        "backtest": h.backtest or {},
        "strategy_id": h.strategy_id,
    }


def _event_dict(e: HypothesisEvent) -> dict:
    return {
        "ts": e.ts.isoformat() if e.ts else "",
        "from": e.from_stage,
        "to": e.to_stage,
        "actor": e.actor,
        "note": e.note,
    }
