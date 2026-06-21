"""Learning Service.

Attributes each fill to the SMEs that drove it, then - once enough price action
has elapsed - scores whether each SME's directional call was right, updates
their vote weights, and runs promotion/demotion gates (paper->live readiness).

In synthetic/offline mode the outcomes are noisy, but the *mechanism* (closed
feedback loop that changes who gets influence) is the point.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ats.core import state
from ats.core.db import session_scope
from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.core.models import Attribution, Decision, SmeTrackRecord
from ats.services.learning.scoring import promotion_decision, update_record

log = get_logger("ats.learning")

# KvState key recording the attribution config in force (auditable across
# restarts; in-flight attributions themselves persist in the DB).
_HORIZON_KEY = "learning.horizon_days"


def _sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


class LearningService:
    name = "learning"

    def __init__(self) -> None:
        self._md = None
        self._horizon_days = 5

    async def start(self, ctx) -> None:
        self._md = ctx.orchestrator.get("market_data")
        from ats.core.config import get_settings

        settings = get_settings()
        self._horizon_days = max(0, settings.learning_horizon_days)
        # Snapshot the active attribution config (auditable; restart-safe).
        prev = state.get_kv(_HORIZON_KEY).get("days")
        if prev is not None and int(prev) != self._horizon_days:
            log.info("learning_horizon_changed",
                     extra={"from": prev, "to": self._horizon_days})
        state.set_kv(_HORIZON_KEY, {"days": self._horizon_days})

        ctx.bus.subscribe(Topic.FILL, self._on_fill)
        ctx.scheduler.add_job(
            self.evaluate, "interval",
            seconds=max(120, settings.agent_cycle_interval_s * 2),
            id="learning_eval", max_instances=1, coalesce=True,
        )

    async def _on_fill(self, evt) -> None:
        p = evt.payload
        decision_id = p.get("decision_id")
        if not decision_id:
            return
        with session_scope() as s:
            d = s.get(Decision, decision_id)
            contributors = d.contributors if d else {}
            s.add(
                Attribution(
                    decision_id=decision_id,
                    symbol=p.get("symbol"),
                    side=p.get("side", "BUY"),
                    entry_price=p.get("fill_price", 0.0),
                    contributors=contributors,
                )
            )

    def evaluate(self, force: bool = False) -> dict:
        """Resolve attributions whose forward-return horizon has elapsed.

        An attribution is scored only once ``learning_horizon_days`` have passed
        since the fill, so the SME's call is judged on a meaningful horizon (5d
        swing by default) rather than the next price tick. ``force`` bypasses
        the horizon for tests/manual evaluation. In-flight (unevaluated) rows
        live in the DB, so a mid-month restart resumes them without loss.
        """
        if self._md is None:
            return {"evaluated": 0}
        cutoff = None
        if not force and self._horizon_days > 0:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cutoff = now - timedelta(days=self._horizon_days)
        evaluated = 0
        with session_scope() as s:
            rows = s.execute(
                select(Attribution).where(Attribution.evaluated.is_(False))
            ).scalars().all()
            for attr in rows:
                if cutoff is not None and attr.ts is not None and attr.ts > cutoff:
                    continue  # horizon not yet elapsed; leave in-flight
                price = self._md.latest_price(attr.symbol)
                if price is None or attr.entry_price <= 0:
                    continue
                fwd = (price - attr.entry_price) / attr.entry_price
                attr.forward_return = round(fwd, 5)
                attr.evaluated = True
                evaluated += 1
                self._score_contributors(s, attr.contributors, fwd)
        if evaluated:
            self._run_promotion()
            log.info("learning_evaluated",
                     extra={"count": evaluated, "horizon_days": self._horizon_days})
        return {"evaluated": evaluated}

    def _score_contributors(self, session, contributors: dict, fwd: float) -> None:
        fwd_sign = _sign(fwd)
        if fwd_sign == 0:
            return
        for sme, info in contributors.items():
            contribution = float(info.get("contribution", 0.0))
            if contribution == 0.0:
                continue
            conviction = float(info.get("conviction", 0.0))
            correct = _sign(contribution) == fwd_sign
            tr = session.get(SmeTrackRecord, sme)
            if tr is None:
                tr = SmeTrackRecord(sme=sme, status="shadow")
                session.add(tr)
                session.flush()
            updated = update_record(
                n=tr.n, wins=tr.wins, brier_sum=tr.brier, pnl_contrib=tr.pnl_contrib,
                correct=correct, conviction=conviction,
                contribution_return=contribution * fwd,
            )
            tr.n = updated["n"]
            tr.wins = updated["wins"]
            tr.hit_rate = updated["hit_rate"]
            tr.brier = updated["brier"]
            tr.pnl_contrib = updated["pnl_contrib"]
            tr.vote_weight = updated["vote_weight"]

    def _run_promotion(self) -> None:
        with session_scope() as s:
            for tr in s.execute(select(SmeTrackRecord)).scalars().all():
                new_status, promoted_weight = promotion_decision(tr.n, tr.hit_rate, tr.status)
                if new_status != tr.status or promoted_weight != tr.promoted_weight:
                    log.info(
                        "sme_status_change",
                        extra={"sme": tr.sme, "from": tr.status, "to": new_status,
                               "hit_rate": tr.hit_rate, "n": tr.n},
                    )
                tr.status = new_status
                tr.promoted_weight = promoted_weight

    def leaderboard(self, limit: int = 20) -> list[dict]:
        with session_scope() as s:
            rows = s.execute(
                select(SmeTrackRecord).order_by(SmeTrackRecord.vote_weight.desc())
            ).scalars().all()
            return [
                {"sme": r.sme, "n": r.n, "hit_rate": r.hit_rate, "brier": r.brier,
                 "vote_weight": r.vote_weight, "pnl_contrib": r.pnl_contrib, "status": r.status}
                for r in rows[:limit]
            ]
