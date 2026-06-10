"""Dashboard Service.

Bridges the event bus to the WebSocket hub (live event ticker) and broadcasts a
full snapshot on a short cadence so the UI stays current without polling.
"""

from __future__ import annotations

from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.server.hub import get_hub
from ats.services.dashboard.snapshot import build_snapshot

log = get_logger("ats.dashboard")

_FORWARD_TOPICS = [
    Topic.FILL, Topic.DECISION, Topic.OPINION, Topic.PROPOSAL,
    Topic.VOLUME_SPIKE, Topic.APPROVAL_REQUEST, Topic.ALERT,
]


class DashboardService:
    name = "dashboard"

    def __init__(self) -> None:
        self._hub = get_hub()
        self._orch = None

    async def start(self, ctx) -> None:
        self._orch = ctx.orchestrator
        for topic in _FORWARD_TOPICS:
            ctx.bus.subscribe(topic, self._forward)
        ctx.scheduler.add_job(
            self.broadcast_snapshot, "interval", seconds=5,
            id="dashboard_snapshot", max_instances=1, coalesce=True,
        )

    async def _forward(self, evt) -> None:
        await self._hub.broadcast({"type": "event", "topic": evt.topic, "payload": evt.payload})

    async def broadcast_snapshot(self) -> None:
        await self._hub.broadcast({"type": "snapshot", "data": build_snapshot(self._orch)})
