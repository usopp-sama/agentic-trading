"""Analytics API (QA-7): per-symbol snapshots, movers, and the screener.

Read-only endpoints backing the Charts overlays, the Opportunities badges, the
Today movers panel, and the /screener page. Everything comes from the
persisted ``AnalyticsSnapshot`` rows via ``AnalyticsService`` — no computation
on the request path.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["analytics"])


def _svc(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    return orch.get("analytics") if orch else None


@router.get("/analytics")
def analytics_table(request: Request) -> dict:
    """Metrics row per symbol (the screener feed)."""
    svc = _svc(request)
    return {"rows": svc.table() if svc else []}


@router.get("/analytics/{symbol}")
def analytics_symbol(symbol: str, request: Request) -> dict:
    """Full analytics snapshot for one symbol (summary/levels/patterns/fair value)."""
    svc = _svc(request)
    snap = svc.get(symbol) if svc else None
    return snap or {"symbol": symbol, "empty": True}


@router.get("/movers")
def movers(request: Request) -> dict:
    """Today's gainers / losers / volume-confirmed movers."""
    svc = _svc(request)
    return svc.movers() if svc else {"gainers": [], "losers": [], "volume_confirmed": []}


@router.get("/screener")
def screener(request: Request, preset: str | None = None) -> dict:
    """Run a named preset (value/quality/dividend/momentum/undervalued/
    overvalued) over the metrics table, or return the whole table."""
    svc = _svc(request)
    if not svc:
        return {"rows": [], "presets": [], "preset": preset}
    return {"rows": svc.screener(preset), "presets": svc.presets(), "preset": preset}


@router.post("/analytics/refresh-statements")
def refresh_statements(request: Request) -> dict:
    """Pull financial statements now (P1.3) so fair-value verdicts populate,
    then recompute the analytics snapshots. Runs in the request threadpool
    (sync handler) so it never blocks the event loop; may take ~30-60s on the
    first run over the network."""
    orch = getattr(request.app.state, "orchestrator", None)
    fundamentals = orch.get("fundamentals") if orch else None
    if fundamentals is None or not hasattr(fundamentals, "refresh_statements"):
        return {"status": "unavailable"}
    rows = fundamentals.refresh_statements()
    analytics = orch.get("analytics") if orch else None
    refreshed = 0
    if analytics is not None:
        try:
            refreshed = analytics.run_close_pass()   # so verdicts appear now
        except Exception:  # noqa: BLE001
            pass
    return {"status": "ok", "statement_rows": rows, "symbols_rescored": refreshed}
