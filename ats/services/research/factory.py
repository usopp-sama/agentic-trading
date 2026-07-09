"""Research factory: the slow loop's scheduler + runner (plan §3).

Turns the 26-persona chorus into a small research staff on a calendar:

- **Saturday 10:00 IST** — weekly pass: macro analyst, fundamentals analyst,
  strategy researcher (hypotheses land in the registry).
- **First Sunday 10:30 IST** — monthly pass: risk reviewer, then the
  committee, whose bounded allocation recommendation waits for human
  approval on the dashboard before it tilts anything.
- **Nightly 20:00 IST** — LLM-free maintenance: news-archive digest note +
  event-calendar reload (feeds the fast-loop veto).

Budget by construction: autonomous runs check month-to-date LLM spend
against ``ATS_LLM_MONTHLY_BUDGET_INR`` and skip (with an audit note) when
exhausted. Manual dashboard triggers still work — you clicked, you pay.
The slow loop never acts during a session: outputs only ever adjust weights
at the next reallocation, orders remain the fast loop's monopoly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from ats.core import state
from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import AllocationRecommendation, NewsItem, ResearchNote
from ats.core.telemetry import instrument
from ats.services.research import hypotheses as registry
from ats.services.research import roles as R

log = get_logger("ats.research.factory")

_LAST_RUNS_KEY = "research:last_runs"
_SEED_KEY = "research:seeded"
_TILT_KEY = "research:committee_tilt"

# Hypotheses #1 and #2 (plan §4) — the operator's flow instinct, made honest.
_SEED_HYPOTHESES = [
    {
        "agent": "human",
        "title": "Flow-anomaly veto: refuse entries on pump signatures",
        "thesis": (
            "Operator-driven pumps in illiquid names have a signature: sharp price "
            "rise on abnormal volume without delivery backing. Entering such names "
            "is buying someone's exit liquidity; a veto should refuse them."
        ),
        "rule": (
            "VETO new entries in symbol S when, over the last 5 sessions: "
            "price change > +10% AND volume z-score (20d) > 3 AND delivery % "
            "declining vs its 20d mean. Veto lasts until the signature clears. "
            "Exits always pass. Universe: full watchlist. Defensive only."
        ),
        "params": {"px_chg_5d": 0.10, "vol_z": 3.0, "delivery_trend": "falling"},
        "universe": ["watchlist"],
        "evidence": "SEBI PFUTP enforcement history; pump/dump microstructure literature.",
    },
    {
        "agent": "human",
        "title": "Institutional-flow momentum in liquid names",
        "thesis": (
            "Delivery-backed volume surges plus bulk/block-deal disclosures in "
            "LIQUID names may mark durable institutional accumulation worth riding "
            "with strict stops — only if hypothesis #1's data looks promising."
        ),
        "rule": "",  # deliberately unspecified until Hyp A's data supports it
        "params": {},
        "universe": ["NIFTY-50 constituents"],
        "evidence": "Bulk/block deal disclosures; delivery-percentage shifts (public NSE data).",
    },
    {
        "agent": "human",
        "title": "Confluence: composite summary + level support",
        "thesis": (
            "A strongly bullish composite technical read (trend + momentum + "
            "volume all agreeing) is a higher-quality entry when it happens at a "
            "price floor — buying the dip in an uptrend rather than chasing."
        ),
        "rule": (
            "BUY symbol S when the 12-check technical_summary score >= +6 AND "
            "price is within 1% of a classic-pivot or Fibonacci support level. "
            "Exit when the summary score rolls over to <= 0. Long-only, "
            "watchlist universe. Implemented as sleeve 'tech_confluence' (shadow)."
        ),
        "params": {"buy_score": 6, "near_pct": 1.0},
        "universe": ["watchlist"],
        "evidence": "Confluence/multiple-timeframe literature; the QA-3 composite + QA-1 levels.",
    },
]


class ResearchFactoryService:
    name = "research"

    def __init__(self, llm=None, committee_llm=None) -> None:
        # Injectable for tests; lazily built from config otherwise.
        self._llm = llm
        self._committee_llm = committee_llm
        self._orch = None

    # --- lifecycle -----------------------------------------------------------
    async def start(self, ctx) -> None:
        settings = get_settings()
        self._orch = ctx.orchestrator
        self.seed_default_hypotheses()
        if not settings.research_enabled:
            log.info("research_disabled")
            return

        from ats.services.market_data.calendar import IST

        ctx.scheduler.add_job(
            self.run_weekly, "cron", day_of_week="sat", hour=10, minute=0,
            timezone=IST, id="research_weekly", max_instances=1, coalesce=True,
        )
        # APScheduler ANDs day and day_of_week → first Sunday of the month.
        ctx.scheduler.add_job(
            self.run_monthly, "cron", day="1-7", day_of_week="sun",
            hour=10, minute=30, timezone=IST,
            id="research_monthly", max_instances=1, coalesce=True,
        )
        ctx.scheduler.add_job(
            self.nightly_maintenance, "cron", hour=20, minute=0, timezone=IST,
            id="research_nightly", max_instances=1, coalesce=True,
        )
        log.info("research_factory_started",
                 extra={"budget_inr": settings.llm_monthly_budget_inr})

    # --- seeds ------------------------------------------------------------------
    def seed_default_hypotheses(self) -> None:
        if state.get_kv(_SEED_KEY).get("done"):
            return
        for spec in _SEED_HYPOTHESES:
            h = registry.propose(
                agent=spec["agent"], title=spec["title"], thesis=spec["thesis"],
                evidence=spec["evidence"], params=spec["params"],
                universe=spec["universe"],
            )
            if spec["rule"]:
                registry.specify(h["id"], rule=spec["rule"],
                                 params=spec["params"], actor=spec["agent"])
        state.set_kv(_SEED_KEY, {"done": True, "n": len(_SEED_HYPOTHESES)})
        log.info("research_seeded", extra={"n": len(_SEED_HYPOTHESES)})

    # --- scheduled passes ----------------------------------------------------------
    def run_weekly(self) -> dict:
        return {"pass": "weekly",
                "roles": [self.run_role(r) for r in R.WEEKLY_ROLES]}

    def run_monthly(self) -> dict:
        # Risk review first so the committee can read it.
        return {"pass": "monthly",
                "roles": [self.run_role(r) for r in R.MONTHLY_ROLES]}

    @instrument("research", "run_role")
    def run_role(self, role: str, actor: str = "scheduler") -> dict:
        """One role pass: budget gate → grounded context → LLM → persist."""
        if role not in R.ROLES:
            return {"role": role, "ok": False, "error": "unknown role"}

        # QA-8.4: the weekly fundamentals pass is deterministic by default —
        # F-score/verdict red flags + screener hits from the analytics engine,
        # zero LLM spend. The LLM version stays for manual (human) runs.
        if (role == "fundamentals_analyst" and actor != "human"
                and not get_settings().research_fundamentals_llm):
            return self._deterministic_fundamentals(role)

        budget = self.budget_status()
        if actor != "human" and budget["exhausted"]:
            self._note(role, f"{R.ROLES[role]['name']} — skipped",
                       "Autonomous run skipped: monthly LLM budget exhausted.",
                       {"skipped": "budget", **budget})
            log.warning("research_skipped_budget", extra={"role": role, **budget})
            return {"role": role, "ok": False, "skipped": "budget", **budget}

        extra = self._committee_extra() if role == "committee" else None
        ctx = R.build_context(role, orchestrator=self._orch, extra=extra)
        user = R.render_user_message(role, ctx)
        llm = self._client(role)
        try:
            reply = llm.chat(R.ROLES[role]["system"],
                             [{"role": "user", "content": user}], json_mode=True)
        except Exception as exc:  # noqa: BLE001 — a bad provider must not kill the pass
            self._note(role, f"{R.ROLES[role]['name']} — failed", str(exc),
                       {"error": True})
            log.warning("research_role_failed", extra={"role": role, "error": str(exc)})
            return {"role": role, "ok": False, "error": str(exc)}

        parsed = R.parse_output(reply)
        result = self._persist(role, parsed, reply)
        self._mark_run(role)
        log.info("research_role_ran",
                 extra={"role": role, "actor": actor, "parsed": parsed is not None})
        return {"role": role, "ok": True, "parsed": parsed is not None, **result}

    def _deterministic_fundamentals(self, role: str) -> dict:
        """LLM-free fundamentals note from the analytics engine (QA-8.4): scan
        the metrics table for red flags (weak F-score, overvalued) and surface
        the current screener hits so the slow loop reads pre-digested tables
        instead of paying the LLM to remember fundamentals."""
        analytics = self._orch.get("analytics") if self._orch else None
        if analytics is None:
            self._note(role, "Fundamentals scan — skipped",
                       "Analytics service unavailable.", {"llm": False})
            return {"role": role, "ok": False, "reason": "no_analytics"}

        rows = analytics.table()
        flags: list[str] = []
        for r in rows:
            sym, f, v = r.get("symbol"), r.get("f_score"), r.get("verdict")
            if f is not None and f <= 2:
                flags.append(f"{sym}: weak fundamentals (Piotroski F={f})")
            if v == "overvalued":
                flags.append(f"{sym}: overvalued vs fair value ({r.get('mos_pct')}%)")
        hits = {p: [x["symbol"] for x in analytics.screener(p)[:10]]
                for p in analytics.presets()}

        lines = ["Red flags: " + ("; ".join(flags[:15]) if flags
                                   else "none in the screened universe.")]
        for preset, syms in hits.items():
            if syms:
                lines.append(f"{preset.title()} screen: " + ", ".join(syms[:10]))
        self._note(
            role, f"Fundamentals scan {date.today().isoformat()} (deterministic)",
            "\n".join(lines),
            {"llm": False, "red_flags": flags[:30], "screener_hits": hits,
             "universe": len(rows)},
        )
        self._mark_run(role)
        log.info("research_fundamentals_deterministic",
                 extra={"flags": len(flags), "universe": len(rows)})
        return {"role": role, "ok": True, "llm": False, "flags": len(flags)}

    def nightly_maintenance(self) -> dict:
        """LLM-free nightly pass: archive digest note + veto-calendar reload."""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        with session_scope() as s:
            n_news = int(s.execute(
                select(func.count()).select_from(NewsItem).where(NewsItem.ts >= cutoff)
            ).scalar() or 0)
        moods = R.sentiment_by_symbol(days=1, min_count=2)
        movers = sorted(moods.items(), key=lambda kv: abs(kv[1]), reverse=True)[:8]
        content = (
            f"{n_news} items archived in 24h. "
            + ("Sentiment movers: "
               + ", ".join(f"{s} {v:+.2f}" for s, v in movers) + "."
               if movers else "No concentrated sentiment.")
        )
        self._note("nightly_digest", f"Nightly digest {date.today().isoformat()}",
                   content, {"news_24h": n_news, "movers": dict(movers)})

        reloaded = False
        event_risk = self._orch.get("event_risk") if self._orch else None
        if event_risk is not None:
            try:
                event_risk.calendar.reload()
                reloaded = True
            except Exception as exc:  # noqa: BLE001
                log.warning("calendar_reload_failed", extra={"error": str(exc)})
        self._mark_run("nightly_digest")
        return {"news_24h": n_news, "calendar_reloaded": reloaded}

    # --- committee approval flow -----------------------------------------------------
    def approve_recommendation(self, rec_id: int, actor: str = "human") -> dict:
        settings = get_settings()
        with session_scope() as s:
            rec = s.get(AllocationRecommendation, rec_id)
            if rec is None:
                return {"status": "not_found"}
            if rec.status != "pending":
                return {"status": rec.status, "reason": "already decided"}
            tilts = R.clamp_tilts(rec.tilts, settings.committee_max_tilt)
            rec.status = "approved"
            rec.actor = actor
            rec.responded_ts = datetime.now(timezone.utc)
        state.set_kv(_TILT_KEY, {"tilts": tilts, "rec_id": rec_id,
                                 "approved_ts": datetime.now(timezone.utc).isoformat()})
        state.audit(actor, "research.recommendation.approve",
                    {"rec_id": rec_id, "tilts": tilts})
        log.info("recommendation_approved", extra={"rec_id": rec_id, "tilts": tilts})
        return {"status": "approved", "rec_id": rec_id, "tilts": tilts}

    def reject_recommendation(self, rec_id: int, actor: str = "human") -> dict:
        with session_scope() as s:
            rec = s.get(AllocationRecommendation, rec_id)
            if rec is None:
                return {"status": "not_found"}
            if rec.status != "pending":
                return {"status": rec.status, "reason": "already decided"}
            rec.status = "rejected"
            rec.actor = actor
            rec.responded_ts = datetime.now(timezone.utc)
        state.audit(actor, "research.recommendation.reject", {"rec_id": rec_id})
        return {"status": "rejected", "rec_id": rec_id}

    # --- budget ---------------------------------------------------------------------
    def budget_status(self) -> dict:
        """Month-to-date spend vs the hard cap.

        Uses a days-window that reaches back to (roughly) the 1st; on the
        first days of a month it may count a sliver of last month — that
        errs conservative, which is the right direction for a hard cap.
        """
        from ats.services.agents.llm_log import usage_summary

        settings = get_settings()
        used = float(usage_summary(days=max(1, date.today().day)).get("est_inr", 0.0))
        budget = settings.llm_monthly_budget_inr
        return {
            "budget_inr": budget,
            "used_inr": round(used, 2),
            "exhausted": bool(budget > 0 and used >= budget),
        }

    # --- introspection (dashboard) ----------------------------------------------------
    def status(self) -> dict:
        return {
            "enabled": get_settings().research_enabled,
            "budget": self.budget_status(),
            "last_runs": state.get_kv(_LAST_RUNS_KEY),
            "roles": {rid: {"name": spec["name"], "cadence": spec["cadence"]}
                      for rid, spec in R.ROLES.items()},
            "active_tilt": state.get_kv(_TILT_KEY),
        }

    # --- internals ---------------------------------------------------------------------
    def _client(self, role: str):
        """Committee gets the stronger (CIO-tier) model; weekly roles the base."""
        if self._llm is None:
            from ats.services.agents.llm_client import select_llm_clients

            sme, cio, _status = select_llm_clients()
            self._llm, self._committee_llm = sme, cio
        return self._committee_llm if role == "committee" and self._committee_llm else self._llm

    def _committee_extra(self) -> dict:
        from ats.services.reference import STRATEGIES

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=35)
        with session_scope() as s:
            notes = s.execute(
                select(ResearchNote).where(ResearchNote.ts >= cutoff)
                .order_by(ResearchNote.ts.desc()).limit(10)
            ).scalars().all()
            recent = [{"role": n.role, "title": n.title,
                       "content": n.content[:800]} for n in notes]
        return {
            "recent_notes": recent,
            "tradeable_sleeves": [sid for sid, _n, _t, st in STRATEGIES if st == "paper"],
        }

    def _persist(self, role: str, parsed: dict | None, raw: str) -> dict:
        """Route a role's output to the right table."""
        spec = R.ROLES[role]
        if parsed is None:
            # Unparseable (e.g. the mock provider): keep the raw reply as a
            # note so nothing is lost, but never create registry rows from it.
            self._note(role, f"{spec['name']} — unparsed reply", raw[:4000],
                       {"parse_error": True})
            return {"notes": 1, "hypotheses": 0, "recommendations": 0}

        if role == "strategy_researcher":
            created = 0
            for h in (parsed.get("hypotheses") or [])[:2]:
                title = str(h.get("title", "")).strip()
                rule = str(h.get("rule", "")).strip()
                if not title or not rule:
                    continue  # unspecifiable ideas do not enter the registry
                row = registry.propose(
                    agent=role, title=title, thesis=str(h.get("thesis", "")),
                    evidence=str(h.get("evidence", "")),
                    params=h.get("params") or {},
                    universe=h.get("universe") or [],
                )
                registry.specify(row["id"], rule=rule,
                                 params=h.get("params") or {},
                                 universe=h.get("universe") or [], actor=role)
                created += 1
            if not created:
                self._note(role, f"{spec['name']} — no proposals",
                           "Pass completed; evidence did not support a new hypothesis.",
                           {"hypotheses": 0})
            return {"hypotheses": created, "notes": 0 if created else 1,
                    "recommendations": 0}

        if role == "committee":
            settings = get_settings()
            from ats.services.reference import STRATEGIES

            known = {sid for sid, _n, _t, _s in STRATEGIES}
            tilts = R.clamp_tilts(parsed.get("tilts") or {},
                                  settings.committee_max_tilt, known_ids=known)
            with session_scope() as s:
                s.add(AllocationRecommendation(
                    summary=str(parsed.get("summary", ""))[:4000],
                    rationale=str(parsed.get("rationale", ""))[:8000],
                    tilts=tilts,
                ))
            return {"recommendations": 1, "hypotheses": 0, "notes": 0}

        # macro_analyst / fundamentals_analyst / risk_reviewer → notes
        title = f"{spec['name']} — {date.today().isoformat()}"
        content = str(
            parsed.get("commentary") or parsed.get("notes")
            or parsed.get("summary") or ""
        )
        meta = {k: v for k, v in parsed.items()
                if k not in ("commentary", "notes", "summary")}
        self._note(role, title, content, meta)
        return {"notes": 1, "hypotheses": 0, "recommendations": 0}

    @staticmethod
    def _note(role: str, title: str, content: str, meta: dict | None = None) -> None:
        with session_scope() as s:
            s.add(ResearchNote(role=role, title=title[:256],
                               content=content, meta=meta or {}))

    @staticmethod
    def _mark_run(role: str) -> None:
        runs = state.get_kv(_LAST_RUNS_KEY)
        runs[role] = datetime.now(timezone.utc).isoformat()
        state.set_kv(_LAST_RUNS_KEY, runs)
