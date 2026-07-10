"""Component telemetry + health substrate for the Ops Console (P4.1).

A thin, in-memory instrumentation layer: wrap a service entry point with
``@instrument("component")`` or a ``with span("component", "op"):`` block and it
records duration + a defined **outcome** into per-component rollups and a ring
buffer of recent spans. From those we derive each component's **health state**.

Outcomes (the operator's "function calls mapped to defined enums"):
``OK | SLOW | ERROR | SKIPPED | DEGRADED``.
Health: ``OK | IDLE | DEGRADED | DOWN``.

Near-zero hot-path cost; process-local (resets on restart). Separate from
``ats.core.perf`` (which times HTTP requests + the event loop) — the Ops Console
reads both.
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from enum import Enum
from threading import Lock

SLOW_MS = 1000.0
_ERROR_RATE_DEGRADED = 0.30


class Outcome(str, Enum):
    OK = "OK"
    SLOW = "SLOW"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"
    DEGRADED = "DEGRADED"


class Health(str, Enum):
    OK = "OK"
    IDLE = "IDLE"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


_LOCK = Lock()
_SPANS: deque = deque(maxlen=2000)
_COMP: dict[str, dict] = defaultdict(
    lambda: {"calls": 0, "errors": 0, "slow": 0, "sum": 0.0,
             "samples": deque(maxlen=200), "last_ts": 0.0,
             "last_outcome": None, "last_error": None}
)
_OVERRIDE: dict[str, str] = {}   # explicit health (e.g. DOWN on start failure)


def record(component: str, op: str, ms: float, outcome: Outcome, error=None) -> None:
    ov = outcome.value if isinstance(outcome, Outcome) else str(outcome)
    with _LOCK:
        c = _COMP[component]
        c["calls"] += 1
        c["sum"] += ms
        c["samples"].append(ms)
        c["last_ts"] = time.time()
        c["last_outcome"] = ov
        if outcome == Outcome.ERROR:
            c["errors"] += 1
            c["last_error"] = str(error) if error else "error"
        if outcome == Outcome.SLOW or ms >= SLOW_MS:
            c["slow"] += 1
        _SPANS.append({"ts": time.time(), "component": component, "op": op,
                       "ms": round(ms, 1), "outcome": ov,
                       "error": str(error) if error else None})


@contextmanager
def span(component: str, op: str):
    t0 = time.perf_counter()
    outcome, err = Outcome.OK, None
    try:
        yield
    except Exception as e:  # noqa: BLE001 — record then re-raise (behavior preserved)
        outcome, err = Outcome.ERROR, e
        raise
    finally:
        ms = (time.perf_counter() - t0) * 1000.0
        if outcome == Outcome.OK and ms >= SLOW_MS:
            outcome = Outcome.SLOW
        record(component, op, ms, outcome, err)


def instrument(component: str, op: str | None = None):
    """Decorator wrapping a sync or async function in a telemetry span."""
    def deco(fn):
        name = op or fn.__name__
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def awrap(*a, **k):
                with span(component, name):
                    return await fn(*a, **k)
            return awrap

        @functools.wraps(fn)
        def swrap(*a, **k):
            with span(component, name):
                return fn(*a, **k)
        return swrap
    return deco


def mark(component: str, health: Health) -> None:
    with _LOCK:
        _OVERRIDE[component] = health.value if isinstance(health, Health) else str(health)


def clear_mark(component: str) -> None:
    with _LOCK:
        _OVERRIDE.pop(component, None)


def component_health(component: str) -> str:
    if component in _OVERRIDE:
        return _OVERRIDE[component]
    c = _COMP.get(component)
    if not c or c["calls"] == 0:
        return Health.IDLE.value
    err_rate = c["errors"] / max(1, c["calls"])
    if c["last_outcome"] in (Outcome.ERROR.value, Outcome.DEGRADED.value) or err_rate > _ERROR_RATE_DEGRADED:
        return Health.DEGRADED.value
    return Health.OK.value


def health_registry(components=None) -> dict[str, str]:
    with _LOCK:
        names = set(components or []) | set(_COMP) | set(_OVERRIDE)
    return {c: component_health(c) for c in sorted(names)}


def _pct(samples, p) -> float | None:
    if not samples:
        return None
    s = sorted(samples)
    return round(s[int(round((p / 100.0) * (len(s) - 1)))], 1)


def snapshot(components=None) -> dict:
    now = time.time()
    with _LOCK:
        comp = {
            name: {
                "calls": c["calls"], "errors": c["errors"], "slow": c["slow"],
                "avg_ms": round(c["sum"] / c["calls"], 1) if c["calls"] else 0.0,
                "p95_ms": _pct(c["samples"], 95),
                "last_outcome": c["last_outcome"], "last_error": c["last_error"],
                "age_s": round(now - c["last_ts"], 1) if c["last_ts"] else None,
            }
            for name, c in _COMP.items()
        }
        recent = list(_SPANS)[-80:][::-1]
    return {"components": comp, "health": health_registry(components), "recent": recent}


def reset() -> None:
    with _LOCK:
        _SPANS.clear()
        _COMP.clear()
        _OVERRIDE.clear()
