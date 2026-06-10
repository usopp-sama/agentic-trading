"""The orchestrator wires together the event bus, scheduler, and services.

A ``Service`` is any object with an async ``start(ctx)`` and optional async
``stop()``. Services subscribe to bus topics and/or register scheduled jobs in
``start``. The orchestrator owns lifecycle so the whole system starts and stops
cleanly, and so the dashboard can introspect what is running.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ats.core.events import EventBus, build_event_bus
from ats.core.logging import get_logger

log = get_logger("ats.orchestrator")


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
        if not self.scheduler.running:
            self.scheduler.start()
        self._started = True
        log.info("orchestrator_started")

    async def stop(self) -> None:
        if not self._started:
            return
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
