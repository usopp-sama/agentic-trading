"""End-to-end smoke test using FastAPI's TestClient.

Boots the full app (runs lifespan: db init, seeding, orchestrator + all
services), then exercises the control API. Safe to run repeatedly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from ats.server.app import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        print("health:", health)

        state = client.get("/api/state").json()
        print("state:", state)

        # Toggle mode and kill switch to verify control plane + audit chain.
        print("set mode PAPER:", client.post("/api/mode", json={"mode": "PAPER"}).json())
        print("kill engage:", client.post("/api/kill", json={"engage": True, "reason": "smoke"}).json())
        print("kill release:", client.post("/api/kill", json={"engage": False}).json())

        after = client.get("/api/state").json()
        print("audit_chain_ok:", after["audit_chain_ok"])
        assert after["audit_chain_ok"], "audit chain broken"
        assert after["real_money_active"] is False, "real money must be inactive in v1"
    print("SMOKE OK")


if __name__ == "__main__":
    main()
