"""Dashboard mount: multi-page UI, read APIs, and the live WebSocket.

Pages (all share one WebSocket stream + nav + toast notifications):
  /           Overview      - KPIs, positions, watchlist news
  /pipeline   Pipeline      - live flow across services, per-stage activity
  /agents     SME Agents    - roster, opinions, leaderboard
  /news       News          - live feed with sentiment + ticker mapping
  /logs       Logs          - graphical event stream + per-topic rates
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.logging import get_logger
from ats.core.models import SmeOpinion
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


def mount_dashboard(app: FastAPI) -> None:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def page(name: str, title: str):
        def _render(request: Request):
            return templates.TemplateResponse(request, name, {"active": title.lower()})
        return _render

    app.add_api_route("/", page("overview.html", "overview"), response_class=HTMLResponse)
    app.add_api_route("/pipeline", page("pipeline.html", "pipeline"), response_class=HTMLResponse)
    app.add_api_route("/agents", page("agents.html", "agents"), response_class=HTMLResponse)
    app.add_api_route("/news", page("news.html", "news"), response_class=HTMLResponse)
    app.add_api_route("/logs", page("logs.html", "logs"), response_class=HTMLResponse)

    @app.get("/experts", response_class=HTMLResponse)
    def experts_page(request: Request):
        return templates.TemplateResponse(request, "experts.html")

    @app.get("/api/dashboard")
    def dashboard_snapshot(request: Request):
        return build_snapshot(getattr(request.app.state, "orchestrator", None))

    @app.get("/api/pipeline")
    def pipeline(request: Request):
        hub = get_hub()
        counters = hub.topic_counters()
        events = hub.recent_events(300)
        stage_count = {k: 0 for k, _ in STAGES}
        stage_recent: dict[str, list] = {k: [] for k, _ in STAGES}
        for topic, c in counters.items():
            st = TOPIC_STAGE.get(topic)
            if st:
                stage_count[st] += c
        for e in reversed(events):
            st = TOPIC_STAGE.get(e["topic"])
            if st and len(stage_recent[st]) < 6:
                stage_recent[st].append({"ts": e.get("ts"), "topic": e["topic"],
                                         "summary": _event_summary(e["topic"], e.get("payload", {}))})
        return {
            "stages": [
                {"key": k, "label": label, "count": stage_count[k], "recent": stage_recent[k]}
                for k, label in STAGES
            ],
            "counters": counters,
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
