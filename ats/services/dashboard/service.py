"""Dashboard Service.

Bridges the event bus to the WebSocket hub (live event ticker) and broadcasts a
full snapshot on a short cadence so the UI stays current without polling.
"""

from __future__ import annotations

import asyncio

from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.server.hub import get_hub
from ats.services.dashboard.snapshot import build_snapshot

log = get_logger("ats.dashboard")

_FORWARD_TOPICS = [
    Topic.VOLUME_SPIKE, Topic.NEWS, Topic.SENTIMENT, Topic.SIGNAL,
    Topic.OPINION, Topic.PROPOSAL, Topic.DECISION, Topic.ORDER,
    Topic.FILL, Topic.APPROVAL_REQUEST, Topic.RULE_CHANGE, Topic.ALERT,
    Topic.REGIME, Topic.OPTION_CHAIN,
]


class DashboardService:
    name = "dashboard"

    def __init__(self) -> None:
        self._hub = get_hub()
        self._orch = None
        self._latest: dict | None = None   # cached snapshot (P0.4)

    async def start(self, ctx) -> None:
        self._orch = ctx.orchestrator
        for topic in _FORWARD_TOPICS:
            ctx.bus.subscribe(topic, self._forward)
        ctx.scheduler.add_job(
            self.broadcast_snapshot, "interval", seconds=5,
            id="dashboard_snapshot", max_instances=1, coalesce=True,
        )

    async def _forward(self, evt) -> None:
        ts = evt.ts.isoformat() if hasattr(evt, "ts") and evt.ts else None
        await self._hub.broadcast(
            {"type": "event", "topic": evt.topic, "payload": evt.payload, "ts": ts}
        )

    async def broadcast_snapshot(self) -> None:
        # Build off the loop (DB + service aggregation) and cache it, so the
        # 5s tick never stalls the loop and GET /api/dashboard is O(1) (P0.4).
        snap = await asyncio.to_thread(build_snapshot, self._orch)
        self._latest = snap
        await self._hub.broadcast({"type": "snapshot", "data": snap})

    def snapshot(self) -> dict:
        """The most recent cached snapshot (built by the broadcast tick); builds
        one lazily on the very first call before any tick has run."""
        if self._latest is None:
            self._latest = build_snapshot(self._orch)
        return self._latest
