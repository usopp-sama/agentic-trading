"""Async event bus.

An interface with two implementations:
- ``InMemoryEventBus``: asyncio pub/sub for single-process deployment (default).
- ``RedisStreamBus``: Redis Streams for multi-service deployment (optional).

Services publish typed events (ticks, signals, opinions, decisions, fills) and
subscribe by topic. The in-memory bus keeps the whole system runnable with no
external broker; switching to Redis is a config change.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ats.core.logging import get_logger

log = get_logger("ats.events")


# Canonical topics used across the system.
class Topic:
    TICK = "market.tick"
    BAR = "market.bar"
    VOLUME_SPIKE = "market.volume_spike"
    NEWS = "news.item"
    SENTIMENT = "news.sentiment"
    SIGNAL = "strategy.signal"
    OPINION = "agent.opinion"
    PROPOSAL = "agent.proposal"
    DECISION = "exec.decision"
    ORDER = "exec.order"
    FILL = "exec.fill"
    APPROVAL_REQUEST = "exec.approval_request"
    RULE_CHANGE = "rules.change"
    ALERT = "system.alert"


@dataclass
class Event:
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    async def publish(self, topic: str, payload: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    def subscribe(self, topic: str, handler: Handler) -> None:  # pragma: no cover
        raise NotImplementedError

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._running = False

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        await self._queue.put(Event(topic=topic, payload=payload))

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                event = await self._queue.get()
            except asyncio.CancelledError:  # pragma: no cover
                break
            handlers = list(self._handlers.get(event.topic, []))
            for handler in handlers:
                try:
                    await handler(event)
                except Exception:  # noqa: BLE001 - one bad handler must not kill the bus
                    log.exception("handler_error", extra={"topic": event.topic})


def build_event_bus() -> EventBus:
    """Factory honoring ``ATS_EVENT_BUS`` (memory|redis)."""
    from ats.core.config import get_settings

    settings = get_settings()
    if settings.event_bus == "redis":
        try:
            return RedisStreamBus(settings.redis_url)
        except Exception:  # noqa: BLE001
            log.warning("redis_bus_unavailable_falling_back_to_memory")
    return InMemoryEventBus()


class RedisStreamBus(EventBus):  # pragma: no cover - exercised only with Redis present
    """Redis Streams bus. Optional; requires the ``redis`` package + a server."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis  # imported lazily

        self._redis = redis.from_url(url, decode_responses=True)
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        import json

        await self._redis.xadd(topic, {"data": json.dumps(payload, default=str)})

    async def start(self) -> None:
        self._running = True
        for topic in self._handlers:
            self._tasks.append(asyncio.create_task(self._consume(topic)))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()

    async def _consume(self, topic: str) -> None:
        import json

        last_id = "$"
        while self._running:
            resp = await self._redis.xread({topic: last_id}, block=1000, count=10)
            for _stream, entries in resp or []:
                for entry_id, fields in entries:
                    last_id = entry_id
                    event = Event(topic=topic, payload=json.loads(fields["data"]))
                    for handler in self._handlers.get(topic, []):
                        await handler(event)
