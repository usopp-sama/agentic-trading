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
