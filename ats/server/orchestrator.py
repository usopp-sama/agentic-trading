"""The orchestrator wires together the event bus, scheduler, and services.

A ``Service`` is any object with an async ``start(ctx)`` and optional async
``stop()``. Services subscribe to bus topics and/or register scheduled jobs in
``start``. The orchestrator owns lifecycle so the whole system starts and stops
cleanly, and so the dashboard can introspect what is running.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ats.core import perf
from ats.core.events import EventBus, build_event_bus
from ats.core.logging import get_logger

log = get_logger("ats.orchestrator")


def _on_job_event(event) -> None:
    """Feed APScheduler job lifecycle into perf telemetry (P0.1)."""
    jid = getattr(event, "job_id", "?")
    code = event.code
    if code == EVENT_JOB_SUBMITTED:
        perf.job_started(jid)
    elif code == EVENT_JOB_MISSED:
        perf.job_finished(jid, missed=True)
    else:
        perf.job_finished(jid, error=(code == EVENT_JOB_ERROR))


async def _loop_lag_probe() -> None:
    """A 1 s heartbeat that reports how late its own wake-up is — the direct
    measure of the event loop being blocked by synchronous work (P0.1)."""
    interval = 1.0
    while True:
        t0 = time.perf_counter()
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        lag_ms = (time.perf_counter() - t0 - interval) * 1000.0
        if lag_ms > perf.LAG_THRESHOLD_MS:
            perf.record_lag(lag_ms)
            log.warning("event_loop_lag",
                        extra={"lag_ms": round(lag_ms, 1), "job": perf.current_job()})


@dataclass
class ServiceContext:
    """Everything a service needs to wire itself up."""

    bus: EventBus
    scheduler: AsyncIOScheduler
    orchestrator: "Orchestrator"


class Service(Protocol):
    name: str

    async def start(self, ctx: ServiceContext) -> None: ...


@dataclass
class Orchestrator:
    bus: EventBus = field(default_factory=build_event_bus)
    scheduler: AsyncIOScheduler = field(default_factory=AsyncIOScheduler)
    services: list[Service] = field(default_factory=list)
    _started: bool = False
    _lag_task: asyncio.Task | None = None
    # Shared service handles other components/routes can reach.
    registry: dict[str, object] = field(default_factory=dict)

    def register(self, service: Service) -> None:
        self.services.append(service)
        self.registry[getattr(service, "name", service.__class__.__name__)] = service

    def get(self, name: str) -> object | None:
        return self.registry.get(name)

    async def start(self) -> None:
        if self._started:
            return
        log.info("orchestrator_starting", extra={"services": len(self.services)})
        await self.bus.start()
        ctx = ServiceContext(bus=self.bus, scheduler=self.scheduler, orchestrator=self)
        for service in self.services:
            try:
                await service.start(ctx)
                log.info("service_started", extra={"service": service.name})
            except Exception:  # noqa: BLE001
                log.exception("service_start_failed", extra={"service": service.name})
        # Perf telemetry (P0.1): job timings + the event-loop lag probe.
        try:
            self.scheduler.add_listener(
                _on_job_event,
                EVENT_JOB_SUBMITTED | EVENT_JOB_EXECUTED
                | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
            )
            self._lag_task = asyncio.create_task(_loop_lag_probe())
        except Exception:  # noqa: BLE001 — telemetry must never block startup
            log.warning("perf_probe_setup_failed")
        if not self.scheduler.running:
            self.scheduler.start()
        self._started = True
        log.info("orchestrator_started")

    async def stop(self) -> None:
        if not self._started:
            return
        if self._lag_task is not None:
            self._lag_task.cancel()
            self._lag_task = None
        for service in reversed(self.services):
            stop = getattr(service, "stop", None)
            if stop:
                try:
                    await stop()
                except Exception:  # noqa: BLE001
                    log.exception("service_stop_failed", extra={"service": service.name})
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        await self.bus.stop()
        self._started = False
        log.info("orchestrator_stopped")
