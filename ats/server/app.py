"""FastAPI application factory and lifespan."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI

from ats.core.config import get_settings
from ats.core.db import init_db
from ats.core.logging import configure_logging, get_logger
from ats.server.orchestrator import Orchestrator

log = get_logger("ats.app")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")
    log.info("starting", extra={"env": settings.env, "mode": settings.trading_mode})
    init_db()

    # Seed reference data (instruments, strategies, baseline rules) if empty.
    from ats.services.bootstrap import seed_all

    seed_all()

    from ats.server.wiring import build_orchestrator

    orch: Orchestrator = build_orchestrator()
    app.state.orchestrator = orch
    await orch.start()
    try:
        yield
    finally:
        await orch.stop()
        log.info("stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agentic Trading Server",
        version="0.1.0",
        lifespan=lifespan,
    )

    from ats.server.api import router as control_router
    from ats.server.experts_api import router as experts_router
    from ats.server.research_api import router as research_router
    from ats.server.results_api import router as results_router

    app.include_router(control_router)
    app.include_router(experts_router)
    app.include_router(research_router)
    app.include_router(results_router)

    # Dashboard (HTML + websocket) is mounted if present.
    with contextlib.suppress(Exception):
        from ats.server.dashboard import mount_dashboard

        mount_dashboard(app)

    # Optional shared-token gate for LAN deployments (off unless configured).
    if settings.dashboard_token:
        from ats.server.auth import TokenGateMiddleware

        app.add_middleware(TokenGateMiddleware, token=settings.dashboard_token)
        log.info("dashboard_token_gate_enabled")

    return app


app = create_app()
