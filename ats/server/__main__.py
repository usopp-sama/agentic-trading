"""Run the server: ``python -m ats.server``."""

from __future__ import annotations

import uvicorn

from ats.core.config import get_settings


def main() -> None:
    settings = get_settings()
    # Bind host/port from config (ATS_HOST / ATS_PORT). Default 127.0.0.1 is
    # this-machine-only; set ATS_HOST=0.0.0.0 to serve the LAN. Never expose
    # publicly without auth + a reverse proxy / VPN (see docs/deployment_lan.md).
    uvicorn.run(
        "ats.server.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_config=None,  # we configure our own structured logging
    )


if __name__ == "__main__":
    main()
