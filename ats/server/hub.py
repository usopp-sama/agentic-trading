"""WebSocket broadcast hub for the dashboard.

A single hub holds all connected dashboard sockets. Services push compact event
messages and periodic snapshots through it. It also keeps a short rolling
history of events and per-topic counters so a freshly opened page (logs,
pipeline) is populated immediately instead of waiting for the next event.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections import defaultdict, deque

from ats.core.logging import get_logger

log = get_logger("ats.hub")

_HISTORY = 300


class DashboardHub:
    def __init__(self) -> None:
        self._connections: set = set()
        self._lock = asyncio.Lock()
        self.last_snapshot: dict | None = None
        self.events: deque[dict] = deque(maxlen=_HISTORY)
        self.counters: dict[str, int] = defaultdict(int)

    async def connect(self, ws) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        # Prime the new client: last snapshot + recent event history + counters.
        with contextlib.suppress(Exception):
            if self.last_snapshot is not None:
                await ws.send_text(json.dumps({"type": "snapshot", "data": self.last_snapshot}))
            await ws.send_text(json.dumps({
                "type": "recent",
                "events": list(self.events),
                "counters": dict(self.counters),
            }, default=str))

    async def disconnect(self, ws) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, message: dict) -> None:
        mtype = message.get("type")
        if mtype == "snapshot":
            self.last_snapshot = message.get("data")
        elif mtype == "event":
            topic = message.get("topic", "?")
            self.counters[topic] += 1
            self.events.append({
                "topic": topic,
                "payload": message.get("payload", {}),
                "ts": message.get("ts"),
            })
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    def recent_events(self, limit: int = 300) -> list[dict]:
        return list(self.events)[-limit:]

    def topic_counters(self) -> dict[str, int]:
        return dict(self.counters)


_hub: DashboardHub | None = None


def get_hub() -> DashboardHub:
    global _hub
    if _hub is None:
        _hub = DashboardHub()
    return _hub
