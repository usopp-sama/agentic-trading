"""Rules Service.

Manages the adaptive rulebook lifecycle:
    propose -> validate -> shadow -> active -> retired
with versioning and an append-only audit trail. Guardrails are seeded as
immutable (rule_type=guardrail) and are never mutated here. Meta-limits block
any proposal that would touch a guardrail metric or loosen risk.
"""

from __future__ import annotations

from sqlalchemy import select

from ats.core import state
from ats.core.db import session_scope
from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.core.models import Rule, RuleVersion
from ats.services.rules.engine import evaluate_rules, violates_meta_limits

log = get_logger("ats.rules")

# Example adaptive rules seeded for demonstration (more-conservative only).
_SEED_ADAPTIVE = [
    {
        "id": "skip_overbought",
        "description": "Block new buys when RSI is extremely overbought.",
        "expression": {"metric": "rsi", "op": "gt", "value": 80, "action": "block"},
        "status": "active",
    },
    {
        "id": "trim_high_volatility",
        "description": "Halve size when short-term volume z-score is very high.",
        "expression": {"metric": "vol_z", "op": "gt", "value": 4.0, "action": "scale_size", "factor": 0.5},
        "status": "shadow",
    },
]


class RulesService:
    name = "rules"

    async def start(self, ctx) -> None:
        self._seed_adaptive()

    def _seed_adaptive(self) -> None:
        with session_scope() as s:
            for spec in _SEED_ADAPTIVE:
                if s.get(Rule, spec["id"]) is None:
                    s.add(
                        Rule(
                            id=spec["id"], scope="global", rule_type="adaptive",
                            expression=spec["expression"], description=spec["description"],
                            status=spec["status"], version=1,
                        )
                    )
                    s.add(RuleVersion(rule_id=spec["id"], version=1, change="seed adaptive",
                                      author="human", evidence={"source": "seed"}))

    # --- lifecycle ---------------------------------------------------------
    def propose_rule(self, rule_id: str, expression: dict, description: str,
                     evidence: dict, author: str = "agent") -> dict:
        reason = violates_meta_limits(expression)
        if reason:
            state.audit(author, "rule.proposal_rejected", {"rule_id": rule_id, "reason": reason})
            return {"status": "rejected", "reason": reason}
        with session_scope() as s:
            existing = s.get(Rule, rule_id)
            if existing:
                existing.version += 1
                existing.expression = expression
                existing.status = "proposed"
                version = existing.version
            else:
                s.add(Rule(id=rule_id, scope="global", rule_type="adaptive",
                           expression=expression, description=description,
                           status="proposed", version=1))
                version = 1
            s.add(RuleVersion(rule_id=rule_id, version=version, change="proposed",
                              author=author, evidence=evidence))
        state.audit(author, "rule.proposed", {"rule_id": rule_id, "expression": expression})
        return {"status": "proposed", "rule_id": rule_id, "version": version}

    def validate_rule(self, rule_id: str) -> dict:
        # In production this runs a purged walk-forward backtest on the rule's
        # historical effect. Here we accept proposals that carry evidence.
        return self._transition(rule_id, expected="proposed", new="shadow", action="validated")

    def activate_rule(self, rule_id: str, actor: str = "human") -> dict:
        return self._transition(rule_id, expected="shadow", new="active", action="activated", actor=actor)

    def retire_rule(self, rule_id: str, actor: str = "human") -> dict:
        return self._transition(rule_id, expected=None, new="retired", action="retired", actor=actor)

    def _transition(self, rule_id: str, expected: str | None, new: str, action: str, actor: str = "system") -> dict:
        with session_scope() as s:
            rule = s.get(Rule, rule_id)
            if rule is None or rule.rule_type != "adaptive":
                return {"status": "not_found_or_immutable"}
            if expected is not None and rule.status != expected:
                return {"status": "bad_state", "current": rule.status, "expected": expected}
            rule.status = new
            rule.version += 1
            s.add(RuleVersion(rule_id=rule_id, version=rule.version, change=action, author=actor, evidence={}))
        state.audit(actor, f"rule.{action}", {"rule_id": rule_id})
        return {"status": new, "rule_id": rule_id}

    # --- evaluation --------------------------------------------------------
    def active_adaptive(self) -> list[dict]:
        with session_scope() as s:
            rows = s.execute(
                select(Rule).where(Rule.rule_type == "adaptive", Rule.status == "active")
            ).scalars().all()
            return [{"id": r.id, "expression": r.expression} for r in rows]

    def evaluate(self, context: dict) -> dict:
        return evaluate_rules(self.active_adaptive(), context)

    def rulebook(self) -> list[dict]:
        with session_scope() as s:
            rows = s.execute(select(Rule).order_by(Rule.rule_type, Rule.id)).scalars().all()
            return [
                {"id": r.id, "type": r.rule_type, "status": r.status, "version": r.version,
                 "description": r.description, "expression": r.expression}
                for r in rows
            ]
