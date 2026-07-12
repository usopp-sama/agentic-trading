"""Ops Console API (P4): system health, telemetry, resources, accounts.

The "engine room" data feed — deep observability separate from the money
dashboard. Everything is read-only aggregation over the telemetry substrate
(``ats.core.telemetry``), the perf ring buffers (``ats.core.perf``), the process
resource sampler, and the account ledgers/demat.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/ops", tags=["ops"])


def _orch(request: Request):
    return getattr(request.app.state, "orchestrator", None)


@router.get("/health")
def ops_health(request: Request) -> dict:
    """Per-component health (OK/IDLE/DEGRADED/DOWN) over every registered
    service, with each service's scheduled jobs' next run times."""
    from ats.core import telemetry

    orch = _orch(request)
    names = sorted(getattr(orch, "registry", {}).keys()) if orch else []
    health = telemetry.health_registry(names)
    next_runs: dict[str, str] = {}
    if orch is not None:
        for job in getattr(orch.scheduler, "get_jobs", lambda: [])():
            if getattr(job, "next_run_time", None):
                next_runs[job.id] = job.next_run_time.isoformat()
    return {
        "started": bool(getattr(orch, "_started", False)) if orch else False,
        "services": names,
        "health": health,
        "next_runs": next_runs,
    }


@router.get("/telemetry")
def ops_telemetry() -> dict:
    """Component rollups (calls/errors/p95/last outcome) + recent spans."""
    from ats.core import telemetry

    return telemetry.snapshot()


@router.get("/resources")
def ops_resources() -> dict:
    """Process RSS/CPU (psutil when installed) + DB/WAL/log sizes."""
    from ats.core.resources import resource_sample

    return resource_sample()


# Per-source free-tier daily budgets — the denominator for the credits gauge.
# Marketaux is intentionally absent: it doesn't bump the kv counter (it self-
# throttles independently and has a tiny 3-article payload).
_NEWS_BUDGETS: dict[str, dict] = {
    "newsapi": {"label": "newsapi.org", "budget": 100, "note": "business/top-headlines IN"},
    "newsdata": {"label": "newsdata.io", "budget": 200, "note": "12 h delayed"},
    "currents": {"label": "currentsapi.services", "budget": 1000, "note": "business IN"},
}


@router.get("/news-credits")
def ops_news_credits() -> dict:
    """Per-source news-API credits used today vs the free-tier daily budget.

    Reads the ``news_credits`` kv counter the keyed collectors bump on every
    successful call (see ``ats.services.scraper.collectors``). Resets implicitly
    at midnight: a counter whose ``day`` isn't today reads as zero used."""
    from datetime import date

    from ats.core import state

    cur = state.get_kv("news_credits") or {}
    today = date.today().isoformat()
    fresh = cur.get("day") == today
    sources = []
    for name, meta in _NEWS_BUDGETS.items():
        used = int(cur.get(name, 0)) if fresh else 0
        budget = int(meta["budget"])
        sources.append({
            "source": name,
            "label": meta["label"],
            "used": used,
            "budget": budget,
            "pct": round(100.0 * used / budget, 1) if budget else 0.0,
            "note": meta["note"],
        })
    return {"day": today, "counting_day": cur.get("day", ""), "sources": sources}


@router.get("/llm-budget")
def ops_llm_budget() -> dict:
    """Month-to-date LLM spend vs the hard monthly cap (``ATS_LLM_MONTHLY_BUDGET_INR``).

    Standalone (doesn't require the research service to be registered): it
    re-derives the same figure ``ResearchFactory.budget_status`` uses — the
    est-INR rollup over a window reaching back to (roughly) the 1st."""
    from datetime import date

    from ats.core.config import get_settings
    from ats.services.agents.llm_log import usage_summary

    used = float(usage_summary(days=max(1, date.today().day)).get("est_inr", 0.0))
    budget = float(get_settings().llm_monthly_budget_inr)
    return {
        "used_inr": round(used, 2),
        "budget_inr": budget,
        "pct": round(100.0 * used / budget, 1) if budget else 0.0,
        "exhausted": bool(budget > 0 and used >= budget),
    }


@router.get("/accounts")
def ops_accounts(request: Request) -> dict:
    """Every trading profile (main + league solos) with bank cash + demat
    holdings — the 'which profile holds what, where' audit (P4.6 / P2)."""
    from ats.services.accounts import demat
    from ats.services.accounts.ledger import AccountLedger

    orch = _orch(request)
    accounts = ["paper"]
    league = orch.get("league") if orch else None
    if league is not None and hasattr(league, "accounts"):
        try:
            accounts += [a for a in league.accounts() if a not in accounts]
        except Exception:  # noqa: BLE001
            pass

    rows = []
    for acc in accounts:
        try:
            cash = AccountLedger(acc).balance().as_dict()
        except Exception:  # noqa: BLE001
            cash = {}
        try:
            dm = demat.account_summary(acc)
        except Exception:  # noqa: BLE001
            dm = {"holdings": [], "pending": 0}
        rows.append({
            "account": acc,
            "cash": cash.get("cash"),
            "available": cash.get("available"),
            "bo_id": dm.get("bo_id"),
            "dp_name": dm.get("dp_name"),
            "pending_settlement": dm.get("pending", 0),
            "holdings": dm.get("holdings", []),
        })
    return {"accounts": rows}
