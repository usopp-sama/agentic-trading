"""Idempotent seeding of reference data into the database."""

from __future__ import annotations

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import Instrument, Rule, RuleVersion, Strategy
from ats.services.reference import GUARDRAILS, STRATEGIES, active_universe

log = get_logger("ats.bootstrap")


def seed_instruments() -> int:
    added = 0
    with session_scope() as s:
        for symbol, name, sector, itype in active_universe():
            if s.get(Instrument, symbol) is None:
                s.add(
                    Instrument(
                        symbol=symbol,
                        name=name,
                        sector=sector,
                        instrument_type=itype,
                        exchange="NSE",
                    )
                )
                added += 1
    return added


def seed_strategies() -> int:
    added = 0
    with session_scope() as s:
        for sid, name, stype, status in STRATEGIES:
            if s.get(Strategy, sid) is None:
                s.add(Strategy(id=sid, name=name, type=stype, status=status))
                added += 1
    return added


def seed_guardrails() -> int:
    added = 0
    with session_scope() as s:
        for g in GUARDRAILS:
            if s.get(Rule, g["id"]) is None:
                s.add(
                    Rule(
                        id=g["id"],
                        scope=g["scope"],
                        rule_type=g["rule_type"],
                        expression=g["expression"],
                        description=g["description"],
                        status="active",
                        version=1,
                    )
                )
                s.add(
                    RuleVersion(
                        rule_id=g["id"],
                        version=1,
                        change="seed guardrail",
                        author="human",
                        evidence={"source": "bootstrap"},
                    )
                )
                added += 1
    return added


def seed_all() -> dict:
    counts = {
        "instruments": seed_instruments(),
        "strategies": seed_strategies(),
        "guardrails": seed_guardrails(),
    }
    log.info("seed_complete", extra=counts)
    return counts
