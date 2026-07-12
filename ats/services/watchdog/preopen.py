"""Pre-open GO/NO-GO self-check (L6).

A daily readiness sweep, run shortly before the NSE open (IST), that answers
one question in one email: *is the system fit to trade today?* It checks the
things a silent failure would otherwise hide until 09:15 — the market-data feed
is warm, the Kite daily token is fresh (when Kite is the source), the disk has
headroom, the LLM budget isn't spent, and the kill switch is clear.

The decision logic (``evaluate_preopen`` / ``format_preopen``) is pure and
unit-tested; ``gather_preopen_checks`` does the I/O and is best-effort.
"""

from __future__ import annotations

import asyncio

from ats.core.config import get_settings
from ats.core.logging import get_logger
from ats.core.telemetry import instrument
from ats.services.execution.notify import notify

log = get_logger("ats.preopen")


# --- pure decision + formatting --------------------------------------------
def evaluate_preopen(checks: list[dict]) -> dict:
    """Fold a list of ``{name, ok, hard, detail}`` checks into a GO/NO-GO.

    GO requires every *hard* check to pass; soft checks are informational and
    never block. Pure."""
    hard = [c for c in checks if c.get("hard")]
    failed = [c["name"] for c in hard if not c.get("ok")]
    return {"go": not failed, "checks": checks, "failed": failed}


def format_preopen(result: dict) -> str:
    """GO/NO-GO result -> a notify() message (first line = subject)."""
    if result["go"]:
        head = "PRE-OPEN GO — system fit to trade today"
    else:
        head = f"PRE-OPEN NO-GO — failed: {', '.join(result['failed'])}"
    lines = [head, ""]
    for c in result["checks"]:
        mark = "[ ok ]" if c.get("ok") else "[FAIL]"
        tag = "" if c.get("hard") else " (info)"
        detail = f" — {c['detail']}" if c.get("detail") else ""
        lines.append(f"  {mark} {c['name']}{tag}{detail}")
    return "\n".join(lines)


# --- I/O gathering ----------------------------------------------------------
def gather_preopen_checks(orch) -> list[dict]:  # pragma: no cover - reads live services
    """Assemble the readiness checks from the running services. Best-effort:
    a probe that raises is reported as a failing check, never propagated."""
    settings = get_settings()
    checks: list[dict] = []

    # 1. Data feed warm — some symbols already priced (or synthetic, always on).
    md = orch.get("market_data") if orch else None
    priced = total = 0
    try:
        if md is not None:
            wl = md.watchlist()
            total = len(wl)
            priced = sum(1 for s in wl if md.latest_price(s) is not None)
    except Exception as exc:  # noqa: BLE001
        log.warning("preopen_feed_probe_failed", extra={"error": str(exc)})
    feed_ok = settings.data_source == "synthetic" or priced > 0
    checks.append({"name": "data_feed", "ok": feed_ok, "hard": True,
                   "detail": f"{priced}/{total} symbols priced ({settings.data_source})"})

    # 2. Kite daily token — hard only when Kite is the live source; otherwise a
    #    soft note if creds exist (so an expired token pre-open is visible).
    kite_source = settings.data_source == "kite"
    has_creds = bool(settings.kite_api_key and settings.kite_api_secret)
    if kite_source or has_creds:
        try:
            from ats.services.market_data.kite_history import get_access_token
            has_token = bool(get_access_token())
        except Exception:  # noqa: BLE001
            has_token = False
        checks.append({"name": "kite_token", "ok": has_token, "hard": kite_source,
                       "detail": "fresh" if has_token else "missing — log in via /kite/login"})

    # 3. Disk headroom on the DB volume.
    checks.append(_disk_check(settings))

    # 4. LLM monthly budget not exhausted.
    checks.append(_budget_check(orch))

    # 5. Kill switch clear.
    try:
        from ats.core import state
        killed = state.is_killed()
    except Exception:  # noqa: BLE001
        killed = False
    checks.append({"name": "kill_switch", "ok": not killed, "hard": True,
                   "detail": "engaged — re-arm before trading" if killed else "clear"})

    return checks


def _disk_check(settings) -> dict:  # pragma: no cover - filesystem
    import os
    import shutil

    min_gb = float(settings.disk_free_min_gb)
    db_path = settings.db_url[len("sqlite:///"):] if settings.db_url.startswith("sqlite:///") else None
    target = os.path.dirname(os.path.abspath(db_path)) if db_path else "."
    try:
        free_gb = shutil.disk_usage(target or ".").free / 1e9
        return {"name": "disk", "ok": free_gb >= min_gb, "hard": True,
                "detail": f"{free_gb:.1f} GB free (min {min_gb:.1f})"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "disk", "ok": True, "hard": True, "detail": f"unmeasured ({exc})"}


def _budget_check(orch) -> dict:  # pragma: no cover - reads research service / DB
    status = None
    research = orch.get("research") if orch else None
    if research is not None and hasattr(research, "budget_status"):
        try:
            status = research.budget_status()
        except Exception:  # noqa: BLE001
            status = None
    if status is None:
        # Standalone recompute if the research service isn't available.
        try:
            from datetime import date
            from ats.services.agents.llm_log import usage_summary
            used = float(usage_summary(days=max(1, date.today().day)).get("est_inr", 0.0))
            budget = float(get_settings().llm_monthly_budget_inr)
            status = {"used_inr": round(used, 2), "budget_inr": budget,
                      "exhausted": bool(budget > 0 and used >= budget)}
        except Exception:  # noqa: BLE001
            status = {"used_inr": 0.0, "budget_inr": 0.0, "exhausted": False}
    return {"name": "llm_budget", "ok": not status.get("exhausted"), "hard": True,
            "detail": f"₹{status.get('used_inr', 0)} / ₹{status.get('budget_inr', 0)}"}


# --- service ----------------------------------------------------------------
class PreOpenCheckService:
    name = "preopen"

    def __init__(self) -> None:
        self._orch = None

    async def start(self, ctx) -> None:
        settings = get_settings()
        if not settings.preopen_check_enabled:
            log.info("preopen_disabled")
            return
        self._orch = ctx.orchestrator
        from ats.services.market_data.calendar import IST

        ctx.scheduler.add_job(
            self.run_check, "cron",
            hour=settings.preopen_hour, minute=settings.preopen_minute,
            timezone=IST, id="preopen_check", max_instances=1, coalesce=True,
        )
        log.info("preopen_scheduled",
                 extra={"hour": settings.preopen_hour, "minute": settings.preopen_minute})

    @instrument("preopen", "run_check")
    async def run_check(self) -> dict:
        # The probes touch the DB / filesystem — keep them off the event loop.
        checks = await asyncio.to_thread(gather_preopen_checks, self._orch)
        result = evaluate_preopen(checks)
        try:
            notify(format_preopen(result))
        except Exception as exc:  # noqa: BLE001 — a failed push must not crash the job
            log.warning("preopen_notify_failed", extra={"error": str(exc)})
        log.info("preopen_check", extra={"go": result["go"], "failed": result["failed"]})
        return result
