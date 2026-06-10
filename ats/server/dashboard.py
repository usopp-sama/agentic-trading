"""Dashboard mount: HTML page, snapshot endpoint, and the live WebSocket."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ats.core.logging import get_logger
from ats.server.hub import get_hub
from ats.services.dashboard.snapshot import build_snapshot

log = get_logger("ats.dashboard")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def mount_dashboard(app: FastAPI) -> None:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request, "dashboard.html")

    @app.get("/api/dashboard")
    def dashboard_snapshot(request: Request):
        orch = getattr(request.app.state, "orchestrator", None)
        return build_snapshot(orch)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        hub = get_hub()
        await hub.connect(websocket)
        try:
            while True:
                # We don't expect client messages; this keeps the socket open.
                await websocket.receive_text()
        except WebSocketDisconnect:
            await hub.disconnect(websocket)
        except Exception:  # noqa: BLE001
            await hub.disconnect(websocket)
