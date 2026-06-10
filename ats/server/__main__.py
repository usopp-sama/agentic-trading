"""Run the server: ``python -m ats.server``."""

from __future__ import annotations

import uvicorn

from ats.core.config import get_settings


def main() -> None:
    settings = get_settings()
    # Bind to localhost by default; never expose publicly without a VPN/Tailscale.
    uvicorn.run(
        "ats.server.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_config=None,  # we configure our own structured logging
    )


if __name__ == "__main__":
    main()
