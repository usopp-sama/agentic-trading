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
from fastapi.responses import HTMLResponse, RedirectResponse
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
    app.add_api_route("/opportunities", page("opportunities.html", "opportunities"), response_class=HTMLResponse)
    app.add_api_route("/charts", page("charts.html", "charts"), response_class=HTMLResponse)
    app.add_api_route("/portfolio", page("portfolio.html", "portfolio"), response_class=HTMLResponse)
    app.add_api_route("/news", page("news.html", "news"), response_class=HTMLResponse)
    app.add_api_route("/experts", page("experts.html", "experts"), response_class=HTMLResponse)
    app.add_api_route("/system", page("system.html", "system"), response_class=HTMLResponse)

    # Legacy paths fold into System (pipeline/agents/logs) or Today (overview).
    for old, target in {"/overview": "/", "/pipeline": "/system",
                        "/agents": "/system", "/logs": "/system"}.items():
        app.add_api_route(old, _redirect(target), response_class=RedirectResponse)

    @app.get("/api/dashboard")
    def dashboard_snapshot(request: Request):
        return build_snapshot(getattr(request.app.state, "orchestrator", None))

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
