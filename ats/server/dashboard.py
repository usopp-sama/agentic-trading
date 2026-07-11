"""Dashboard mount: multi-page UI, read APIs, and the live WebSocket.

Results-first pages (all share one WebSocket stream + nav + toast + theme):
  /               Today         - LLM brief, top opportunities, portfolio, news
  /opportunities  Opportunities - ranked setups the algos found (+ detail)
  /charts         Charts        - live + annotated candlesticks
  /portfolio      Portfolio     - equity curve, holdings, trade blotter
  /news           News          - in-app reader with sentiment + filters
  /experts        Experts       - SME chat / debate / theses / directives
  /system         System        - pipeline + roster + event stream (the firehose)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import (
    Decision,
    Fill,
    NewsItem,
    Ohlcv,
    SentimentScore,
    Signal,
    SmeOpinion,
)
from ats.server.hub import get_hub
from ats.services.dashboard.snapshot import build_snapshot

log = get_logger("ats.dashboard")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Map event topics to pipeline stages (left-to-right flow).
TOPIC_STAGE = {
    "market.tick": "market", "market.bar": "market", "market.volume_spike": "market",
    "news.item": "news",
    "news.sentiment": "nlp",
    "strategy.signal": "strategy",
    "agent.opinion": "agents",
    "agent.proposal": "cio",
    "exec.decision": "risk",
    "exec.order": "execution", "exec.fill": "execution", "exec.approval_request": "execution",
}
STAGES = [
    ("market", "Market Data"), ("news", "News Scraper"), ("nlp", "NLP / Sentiment"),
    ("strategy", "Strategies"), ("agents", "SME Agents"), ("cio", "CIO Aggregator"),
    ("risk", "Risk Manager"), ("execution", "Execution"),
]


def _event_summary(topic: str, p: dict) -> str:
    sym = p.get("symbol") or ",".join(p.get("tickers", []) or []) or ""
    if topic == "agent.opinion":
        return f"{p.get('sme','')} {p.get('stance','')} {sym} ({p.get('conviction','')})"
    if topic == "exec.decision":
        return f"{p.get('action','')} {sym} qty={p.get('qty', p.get('target_qty',''))} {p.get('status','')}"
    if topic == "exec.fill":
        return f"FILL {sym} {p.get('side','')} {p.get('qty','')}@{p.get('fill_price','')}"
    if topic == "market.volume_spike":
        return f"{sym} volume z={p.get('zscore','')}"
    if topic == "news.item":
        return (p.get("title") or "")[:80]
    if topic == "news.sentiment":
        return f"{sym} {p.get('label','')} {p.get('score','')}"
    if topic == "strategy.signal":
        return f"{p.get('strategy','')} {sym} {p.get('stance','')}"
    if topic == "agent.proposal":
        return f"{sym} w={p.get('target_weight','')} conv={p.get('conviction','')}"
    return sym or topic


def _redirect(target: str):
    def _r(request: Request):
        return RedirectResponse(target, status_code=308)
    return _r


# Models whose recent row count stands in for "throughput" of a pipeline stage.
# (market = bars stored; cio has no table, so it stays session-only.)
_STAGE_MODELS = {
    "market": Ohlcv,
    "news": NewsItem,
    "nlp": SentimentScore,
    "strategy": Signal,
    "agents": SmeOpinion,
    "risk": Decision,
    "execution": Fill,
}


def _db_stage_counts(hours: int = 24) -> dict[str, int]:
    """Rows written per stage in the last ``hours`` — so the pipeline is
    informative even after a restart (in-memory counters reset) or when the
    market is closed and nothing new is flowing this session."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    counts = {k: 0 for k, _ in STAGES}
    try:
        with session_scope() as s:
            for stage, model in _STAGE_MODELS.items():
                if model is None:
                    continue
                ts_col = getattr(model, "ts", None) or getattr(model, "day", None)
                if ts_col is None:
                    continue
                counts[stage] = int(
                    s.execute(
                        select(func.count()).select_from(model).where(ts_col >= cutoff)
                    ).scalar() or 0
                )
    except Exception as exc:  # noqa: BLE001 - DB counts are best-effort
        log.warning("pipeline_db_counts_failed", extra={"error": str(exc)})
    return counts


def _read_app_log(limit: int = 300, level: str | None = None, q: str | None = None) -> list[dict]:
    """Tail the rotating JSON log file, newest first.

    Reads only the last ~512 KB so this is cheap even on a large file. Each line
    is a JSON record (see ``ats.core.logging.JsonFormatter``); non-JSON lines are
    surfaced as plain ``msg`` so nothing is silently dropped.
    """
    import json as _json

    from ats.core.config import get_settings

    limit = max(1, min(limit, 1000))
    try:
        s = get_settings()
        path = Path(s.log_dir) / "ats.log"
        if not path.exists():
            return []
        size = path.stat().st_size
        chunk = min(size, 512 * 1024)
        with path.open("rb") as fh:
            fh.seek(size - chunk)
            raw = fh.read().decode("utf-8", errors="replace")
        # Drop a possibly-partial first line when we didn't start at byte 0.
        lines = raw.splitlines()
        if chunk < size and lines:
            lines = lines[1:]
    except Exception as exc:  # noqa: BLE001 - log viewer is best-effort
        log.warning("app_log_read_failed", extra={"error": str(exc)})
        return []

    want = (level or "").upper()
    needle = (q or "").lower()
    out: list[dict] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rec = _json.loads(line)
        except Exception:  # noqa: BLE001
            rec = {"ts": "", "level": "RAW", "logger": "", "msg": line}
        if want and str(rec.get("level", "")).upper() != want:
            continue
        if needle and needle not in line.lower():
            continue
        out.append(rec)
        if len(out) >= limit:
            break
    return out


def mount_dashboard(app: FastAPI) -> None:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def page(name: str, active: str):
        def _render(request: Request):
            return templates.TemplateResponse(request, name, {"active": active})
        return _render

    # Results-first information architecture.
    app.add_api_route("/", page("today.html", "today"), response_class=HTMLResponse)
    app.add_api_route("/control", page("control_room.html", "control"), response_class=HTMLResponse)
    app.add_api_route("/opportunities", page("opportunities.html", "opportunities"), response_class=HTMLResponse)
    app.add_api_route("/strategies", page("strategies.html", "strategies"), response_class=HTMLResponse)
    app.add_api_route("/screener", page("screener.html", "screener"), response_class=HTMLResponse)
    app.add_api_route("/league", page("league.html", "league"), response_class=HTMLResponse)
    app.add_api_route("/research", page("research.html", "research"), response_class=HTMLResponse)
    app.add_api_route("/loops", page("loops.html", "loops"), response_class=HTMLResponse)
    app.add_api_route("/charts", page("charts.html", "charts"), response_class=HTMLResponse)
    app.add_api_route("/portfolio", page("portfolio.html", "portfolio"), response_class=HTMLResponse)
    app.add_api_route("/activity", page("activity.html", "activity"), response_class=HTMLResponse)
    app.add_api_route("/news", page("news.html", "news"), response_class=HTMLResponse)
    app.add_api_route("/experts", page("experts.html", "experts"), response_class=HTMLResponse)
    # Ops Console + its sub-pages (P4 polish: logs/llm/system live under /ops).
    app.add_api_route("/ops", page("ops.html", "ops"), response_class=HTMLResponse)
    app.add_api_route("/ops/system", page("system.html", "ops"), response_class=HTMLResponse)
    app.add_api_route("/ops/logs", page("logs.html", "ops"), response_class=HTMLResponse)
    app.add_api_route("/ops/llm", page("llm.html", "ops"), response_class=HTMLResponse)

    # Legacy paths 308-redirect to their new homes.
    for old, target in {"/overview": "/", "/pipeline": "/ops/system",
                        "/agents": "/ops/system", "/system": "/ops/system",
                        "/logs": "/ops/logs", "/llm": "/ops/llm"}.items():
        app.add_api_route(old, _redirect(target), response_class=RedirectResponse)

    # --- PWA (QA-11): installable dashboard over LAN/VPN ---------------------
    @app.get("/manifest.webmanifest")
    def manifest():
        return JSONResponse(
            {
                "name": "Agentic Trading", "short_name": "ATS",
                "start_url": "/", "scope": "/", "display": "standalone",
                "background_color": "#0c1118", "theme_color": "#0c1118",
                "description": "Deterministic trading control room",
                "icons": [{
                    "src": "/static/icon.svg", "sizes": "any",
                    "type": "image/svg+xml", "purpose": "any maskable",
                }],
            },
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    def service_worker():
        sw = STATIC_DIR / "sw.js"
        text = sw.read_text(encoding="utf-8") if sw.exists() else ""
        # Served from root so the worker's scope covers the whole app.
        return PlainTextResponse(text, media_type="application/javascript")

    # --- Kite login (one-click daily token via the running dashboard) --------
    def _kite_page(msg: str, ok: bool, token: str = "") -> str:
        env_line = (f'<p>For it to survive a restart, also add to <code>.env</code>:'
                    f'<br><code>ATS_KITE_ACCESS_TOKEN={token}</code></p>') if token else ""
        colour = "#34d399" if ok else "#fb7185"
        return (
            f"<!doctype html><meta charset=utf-8><title>Kite login</title>"
            f"<body style='font-family:system-ui;max-width:640px;margin:60px auto;"
            f"padding:24px;background:#0c1118;color:#e8eef5'>"
            f"<h2 style='color:{colour}'>{'✓ Kite connected' if ok else '⚠ Kite login'}</h2>"
            f"<p>{msg}</p>{env_line}"
            f"<p style='margin-top:24px'><a style='color:#2dd4bf' href='/ops'>← Back to Ops Console</a></p>"
            f"</body>"
        )

    @app.get("/kite/login")
    def kite_login(request: Request):
        """Redirect to the Zerodha login page for this app's api_key."""
        from ats.core.config import get_settings
        from ats.services.market_data.kite_history import login_url

        if not get_settings().kite_api_key:
            return HTMLResponse(_kite_page(
                "Set ATS_KITE_API_KEY / ATS_KITE_API_SECRET in .env first "
                "(see docs/kite_setup.md), then reload this.", ok=False))
        return RedirectResponse(login_url(), status_code=302)

    @app.get("/kite/callback")
    def kite_callback(request: Request):
        """Catch Zerodha's redirect: exchange request_token -> access_token and
        store it at runtime (used immediately + by the backtest process)."""
        request_token = request.query_params.get("request_token", "").strip()
        if not request_token:
            return HTMLResponse(_kite_page(
                "No request_token in the redirect — start again from "
                "<a style='color:#2dd4bf' href='/kite/login'>Login with Zerodha</a>.",
                ok=False))
        try:
            from ats.services.market_data.kite_history import (
                exchange_request_token,
                set_access_token,
            )

            token = exchange_request_token(request_token)
            set_access_token(token)
        except Exception as exc:  # noqa: BLE001
            return HTMLResponse(_kite_page(f"Token exchange failed: {exc}", ok=False))
        return HTMLResponse(_kite_page(
            "Historical data is ready. Run the backtest: "
            "<code>python scripts/run_backtests.py --kite --period 1y</code>",
            ok=True, token=token))

    @app.get("/api/kite/status")
    def kite_status():
        from ats.core.config import get_settings
        from ats.services.market_data.kite_history import get_access_token

        s = get_settings()
        try:
            tok = get_access_token()
        except Exception:  # noqa: BLE001
            tok = ""
        return {
            "has_creds": bool(s.kite_api_key and s.kite_api_secret),
            "has_token": bool(tok),
            "callback": "/kite/callback",
        }

    @app.get("/api/perf")
    def perf_snapshot():
        """Live performance telemetry (P0.1): slow requests, event-loop lag,
        and scheduled-job timings — the data behind 'why is it slow?'."""
        from ats.core import perf

        return perf.snapshot()

    @app.get("/api/dashboard")
    def dashboard_snapshot(request: Request):
        # Serve the cached snapshot (refreshed every 5s off-loop by the
        # DashboardService) instead of recomputing per request (P0.4).
        orch = getattr(request.app.state, "orchestrator", None)
        svc = orch.get("dashboard") if orch else None
        if svc is not None and hasattr(svc, "snapshot"):
            return svc.snapshot()
        return build_snapshot(orch)

    @app.get("/api/wallpapers")
    def wallpapers():
        """List background images for the Liquid Glass theme. Drop any
        .jpg/.png/.webp/.svg into ``static/wallpapers/`` and it appears in the
        rotation — no restart, no manifest to edit. Ships a few SVG defaults."""
        exts = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg"}
        wp_dir = STATIC_DIR / "wallpapers"
        files: list[str] = []
        if wp_dir.exists():
            for p in sorted(wp_dir.iterdir()):
                if p.is_file() and p.suffix.lower() in exts:
                    files.append(f"/static/wallpapers/{p.name}")
        return {"wallpapers": files}

    @app.get("/api/pipeline")
    def pipeline(request: Request):
        hub = get_hub()
        counters = hub.topic_counters()
        events = hub.recent_events(300)
        live_count = {k: 0 for k, _ in STAGES}
        stage_recent: dict[str, list] = {k: [] for k, _ in STAGES}
        for topic, c in counters.items():
            st = TOPIC_STAGE.get(topic)
            if st:
                live_count[st] += c
        for e in reversed(events):
            st = TOPIC_STAGE.get(e["topic"])
            if st and len(stage_recent[st]) < 6:
                stage_recent[st].append({"ts": e.get("ts"), "topic": e["topic"],
                                         "summary": _event_summary(e["topic"], e.get("payload", {}))})
        db24 = _db_stage_counts(24)
        return {
            "stages": [
                {
                    "key": k, "label": label,
                    # Headline count = recent persisted throughput (survives
                    # restarts); falls back to this session's live events.
                    "count": max(db24.get(k, 0), live_count[k]),
                    "live": live_count[k],
                    "window24h": db24.get(k, 0),
                    "recent": stage_recent[k],
                }
                for k, label in STAGES
            ],
            "counters": counters,
            "window": "24h",
        }

    @app.get("/api/loops")
    def loops(request: Request):
        """Three-panel state of the three loops (plan §10.2): what each loop
        is doing right now, from the services that own the facts."""
        from ats.core import state as _state
        from ats.core.models import Order
        from ats.services.research import hypotheses as _registry

        orch = getattr(request.app.state, "orchestrator", None)

        def svc(name):
            return orch.get(name) if orch else None

        def safe(obj, method, default=None):
            try:
                fn = getattr(obj, method, None)
                return fn() if fn else default
            except Exception:  # noqa: BLE001 — one sick service must not kill the page
                return default

        # --- fast loop: the protective membrane ---
        with session_scope() as s:
            in_flight = int(s.execute(
                select(func.count(Order.id)).where(
                    Order.status.in_(("STAGED", "SUBMITTED", "ACKED", "PARTIAL"))
                )
            ).scalar() or 0)
        md = svc("market_data")
        fast = {
            "mode": _state.get_mode(),
            "kill_switch": _state.is_killed(),
            "orders_in_flight": in_flight,
            "vetoes": safe(svc("event_risk"), "status", {}),
            "reconciliation": safe(svc("reconcile"), "status", {}),
            "feed": safe(md, "data_status", {}),
            "watchdog": safe(svc("watchdog"), "status", {}),
        }

        # --- medium loop: the quant earner ---
        strategies = svc("strategies")
        live = safe(strategies, "live_state", {"summary": {}}) or {"summary": {}}
        trader = svc("strategy_trader")
        regime = svc("regime")
        medium = {
            "summary": live.get("summary", {}),
            "regime": getattr(safe(regime, "current"), "label", None),
            "consensus": safe(trader, "live_views", {}),
            "committee_tilt": (_state.get_kv("research:committee_tilt") or {}).get("tilts") or {},
            "alloc_weights": {
                r["id"]: r.get("alloc_weight")
                for r in live.get("strategies", []) if r.get("alloc_weight")
            },
        }

        # --- slow loop: the research factory ---
        research = svc("research")
        try:
            kanban_counts = {stage: len(rows)
                             for stage, rows in _registry.by_stage().items()}
        except Exception:  # noqa: BLE001
            kanban_counts = {}
        next_runs: dict[str, str] = {}
        if orch is not None:
            for job in getattr(orch.scheduler, "get_jobs", lambda: [])():
                if job.id.startswith(("research_", "flows_")) and job.next_run_time:
                    next_runs[job.id] = job.next_run_time.isoformat()
        slow = {
            "factory": safe(research, "status", {"enabled": False}),
            "hypotheses": kanban_counts,
            "flows": safe(svc("flows"), "status", {}),
            "next_runs": next_runs,
        }
        return {"fast": fast, "medium": medium, "slow": slow}

    @app.get("/api/agents")
    def agents(request: Request):
        orch = getattr(request.app.state, "orchestrator", None)
        ag = orch.get("agents") if orch else None
        learning = orch.get("learning") if orch else None
        roster = []
        if ag is not None:
            for p in ag.personas():
                roster.append({
                    "id": p.get("id"), "name": p.get("name", p.get("id")),
                    "family": p.get("family", ""), "scope": p.get("scope", ""),
                    "weight": p.get("weight", 0.0), "status": p.get("status", ""),
                })
        with session_scope() as s:
            opinions = [
                {"ts": o.ts.isoformat(), "sme": o.sme, "symbol": o.symbol,
                 "stance": o.stance, "conviction": o.conviction, "rationale": o.rationale}
                for o in s.execute(select(SmeOpinion).order_by(SmeOpinion.id.desc()).limit(40)).scalars().all()
            ]
        return {
            "roster": roster,
            "opinions": opinions,
            "macro_tilt": round(ag.macro_tilt, 4) if ag else 0.0,
            "leaderboard": learning.leaderboard() if learning else [],
        }

    @app.get("/api/logs")
    def logs(request: Request):
        hub = get_hub()
        out = []
        for e in hub.recent_events(300):
            out.append({"ts": e.get("ts"), "topic": e["topic"],
                        "summary": _event_summary(e["topic"], e.get("payload", {})),
                        "stage": TOPIC_STAGE.get(e["topic"], "")})
        return {"events": out, "counters": hub.topic_counters()}

    @app.get("/api/llm/calls")
    def llm_calls(limit: int = 100, kind: str | None = None, ok: bool | None = None):
        """History of real LLM queries (prompt + response) for the LLM tab."""
        from ats.services.agents.llm_log import recent_calls

        calls = recent_calls(limit=limit, kind=kind, ok=ok)
        total = len(calls)
        fails = sum(1 for c in calls if not c.get("ok"))
        ptok = sum(int(c.get("prompt_tokens") or 0) for c in calls)
        ctok = sum(int(c.get("completion_tokens") or 0) for c in calls)
        return {
            "calls": calls,
            "stats": {"shown": total, "errors": fails,
                      "prompt_tokens": ptok, "completion_tokens": ctok},
        }

    @app.get("/api/llm/usage")
    def llm_usage(days: int | None = None):
        """Token + estimated-cost rollup from recorded LLM calls."""
        from ats.services.agents.llm_log import usage_summary

        return usage_summary(days=days)

    @app.get("/api/logs/app")
    def app_logs(limit: int = 300, level: str | None = None, q: str | None = None):
        """Tail of the structured application log file (JSON lines)."""
        return {"lines": _read_app_log(limit=limit, level=level, q=q)}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        hub = get_hub()
        await hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await hub.disconnect(websocket)
        except Exception:  # noqa: BLE001
            await hub.disconnect(websocket)
