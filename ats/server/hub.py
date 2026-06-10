"""WebSocket broadcast hub for the dashboard.

A single hub holds all connected dashboard sockets. Services push compact event
messages and periodic snapshots through it; new clients immediately receive the
last snapshot so the UI is populated on load.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

from ats.core.logging import get_logger

log = get_logger("ats.hub")


class DashboardHub:
    def __init__(self) -> None:
        self._connections: set = set()
        self._lock = asyncio.Lock()
        self.last_snapshot: dict | None = None

    async def connect(self, ws) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        if self.last_snapshot is not None:
            with contextlib.suppress(Exception):
                await ws.send_text(json.dumps({"type": "snapshot", "data": self.last_snapshot}))

    async def disconnect(self, ws) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, message: dict) -> None:
        if message.get("type") == "snapshot":
            self.last_snapshot = message.get("data")
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


_hub: DashboardHub | None = None


def get_hub() -> DashboardHub:
    global _hub
    if _hub is None:
        _hub = DashboardHub()
    return _hub
