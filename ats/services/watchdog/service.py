"""Watchdog Service — the dead-man's switch (roadmap Part 10).

A trading system whose data feed silently dies is more dangerous than
one that is down: positions sit unmanaged while stops and exits never
fire. The watchdog tracks bar heartbeats and, when the feed goes silent
beyond tolerance, alerts loudly and (by default) engages the kill
switch after sustained failure so no NEW risk is added on stale data.

Deliberate asymmetries:
- The watchdog may ENGAGE the kill switch; it never releases it. A
  human re-arms the system after diagnosing the gap.
- For live sources, staleness only counts during NSE market hours
  (a silent feed at midnight is correct behavior). The synthetic
  source is expected to tick continuously, so it is always monitored.

``WatchdogMonitor`` holds the decision logic as a pure state machine so
it is testable without asyncio or services.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ats.core import state
from ats.core.config import get_settings
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger
from ats.core.telemetry import instrument
from ats.services.execution.notify import notify
from ats.services.market_data.calendar import is_market_open

log = get_logger("ats.watchdog")


@dataclass
class WatchdogVerdict:
    healthy: bool
    reason: str
    consecutive_failures: int
    should_kill: bool


_BAD_HEALTH = {"DEGRADED", "DOWN"}


def diff_health(prev: dict[str, str], cur: dict[str, str]) -> tuple[list[str], list[str]]:
    """``(newly_bad, recovered)`` service names between two health snapshots.

    Edge-triggered so alerts fire once per transition, not every check: a
    service is *newly bad* when it enters DEGRADED/DOWN from anything else, and
    *recovered* when it leaves. Pure — the service wraps I/O around it."""
    newly_bad, recovered = [], []
    for name, cur_state in cur.items():
        was = prev.get(name)
        if cur_state in _BAD_HEALTH and was not in _BAD_HEALTH:
            newly_bad.append(name)
        elif was in _BAD_HEALTH and cur_state not in _BAD_HEALTH:
            recovered.append(name)
    return sorted(newly_bad), sorted(recovered)


class WatchdogMonitor:
    """Pure heartbeat state machine (no I/O)."""

    def __init__(self, stale_after_s: float, kill_after_failures: int) -> None:
        self.stale_after_s = stale_after_s
        self.kill_after_failures = kill_after_failures
        self._last_beat: float | None = None
        self._started: float | None = None
        self._failures = 0

    def start(self, now: float) -> None:
        self._started = now

    def record_beat(self, now: float) -> None:
        self._last_beat = now

    def check(self, now: float, feed_expected: bool) -> WatchdogVerdict:
        """Assess feed health; failure count only advances while a feed
        is expected, and a healthy check resets it."""
        if not feed_expected:
            self._failures = 0
            return WatchdogVerdict(True, "feed_not_expected", 0, False)
        baseline = self._last_beat if self._last_beat is not None else self._started
        if baseline is None:
            # start() not called yet; treat as healthy rather than guess.
            return WatchdogVerdict(True, "not_started", 0, False)
        age = now - baseline
        if age <= self.stale_after_s:
            self._failures = 0
            return WatchdogVerdict(True, "fresh", 0, False)
        self._failures += 1
        return WatchdogVerdict(
            healthy=False,
            reason=f"no bars for {int(age)}s (tolerance {int(self.stale_after_s)}s)",
            consecutive_failures=self._failures,
            should_kill=self._failures >= self.kill_after_failures,
        )


class WatchdogService:
    name = "watchdog"

    def __init__(self) -> None:
        settings = get_settings()
        self.monitor = WatchdogMonitor(
            stale_after_s=settings.watchdog_stale_after_s,
            kill_after_failures=settings.watchdog_kill_after_failures,
        )
        self._bus: EventBus | None = None
        self._was_healthy = True
        self._orch = None
        self._svc_health: dict[str, str] = {}

    async def start(self, ctx) -> None:
        self._bus = ctx.bus
        self._orch = ctx.orchestrator
        self.monitor.start(time.monotonic())
        ctx.bus.subscribe(Topic.BAR, self._on_bar)
        ctx.scheduler.add_job(
            self.check_once,
            "interval",
            seconds=get_settings().watchdog_interval_s,
            id="watchdog_check",
            max_instances=1,
            coalesce=True,
        )
        if get_settings().watchdog_health_alerts:
            ctx.scheduler.add_job(
                self.check_component_health,
                "interval",
                seconds=max(30, get_settings().watchdog_interval_s),
                id="watchdog_health",
                max_instances=1,
                coalesce=True,
            )

    async def _on_bar(self, evt) -> None:
        self.monitor.record_beat(time.monotonic())

    def _feed_expected(self) -> bool:
        settings = get_settings()
        if settings.data_source == "synthetic":
            return True  # synthetic ticks around the clock
        return is_market_open()

    @instrument("watchdog", "check_once")
    async def check_once(self) -> WatchdogVerdict:
        settings = get_settings()
        verdict = self.monitor.check(time.monotonic(), self._feed_expected())

        if not verdict.healthy and self._was_healthy:
            log.warning("watchdog_unhealthy", extra={"reason": verdict.reason})
            notify(f"WATCHDOG: data feed unhealthy — {verdict.reason}")
        if verdict.healthy and not self._was_healthy:
            log.info("watchdog_recovered")
            notify("WATCHDOG: data feed recovered (kill switch, if engaged, stays on until re-armed by a human)")
        self._was_healthy = verdict.healthy

        if not verdict.healthy and self._bus is not None:
            await self._bus.publish(
                Topic.ALERT,
                {"kind": "watchdog", "reason": verdict.reason,
                 "consecutive_failures": verdict.consecutive_failures},
            )
        if (
            verdict.should_kill
            and settings.watchdog_auto_kill
            and not state.is_killed()
        ):
            state.engage_kill_switch(actor="watchdog", reason=verdict.reason)
            notify(f"WATCHDOG: kill switch ENGAGED — {verdict.reason}")
        return verdict

    @instrument("watchdog", "check_component_health")
    async def check_component_health(self) -> dict:
        """Edge-triggered alert when any registered service goes DEGRADED/DOWN
        (and again on recovery), so a silently-failing component pages the
        operator instead of just colouring a tile red on the Ops Console."""
        from ats.core import telemetry

        names = sorted(getattr(self._orch, "registry", {}).keys()) if self._orch else []
        cur = telemetry.health_registry(names)
        newly_bad, recovered = diff_health(self._svc_health, cur)
        for svc in newly_bad:
            st = cur.get(svc, "?")
            log.warning("component_unhealthy", extra={"service": svc, "state": st})
            notify(f"HEALTH: {svc} is {st}")
            if self._bus is not None:
                await self._bus.publish(
                    Topic.ALERT,
                    {"kind": "health", "service": svc, "state": st,
                     "reason": f"{svc} → {st}"},
                )
        for svc in recovered:
            log.info("component_recovered", extra={"service": svc, "state": cur.get(svc)})
            notify(f"HEALTH: {svc} recovered ({cur.get(svc)})")
        self._svc_health = cur
        return {"newly_bad": newly_bad, "recovered": recovered}

    # --- introspection -------------------------------------------------------
    def status(self) -> dict:
        return {
            "healthy": self._was_healthy,
            "failures": self.monitor._failures,
        }
