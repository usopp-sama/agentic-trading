"""Lightweight performance telemetry (perf plan P0.1).

In-memory ring buffers with near-zero hot-path cost that answer one question:
*when the dashboard feels slow, what is actually blocking?* Three signals:

- **slow requests** — server-side handler time per HTTP request,
- **event-loop lag** — how late a fixed 1 s heartbeat wakes up (the direct
  measure of the loop being starved by blocking work), tagged with the
  scheduler job in flight at the time,
- **job timings** — per scheduled job duration, errors, and "missed" events.

Exposed at ``GET /api/perf`` and later the Ops Console. No DB, no I/O here; a
process restart resets it (that's fine — it's a live diagnostic).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

# thresholds (ms)
SLOW_REQUEST_MS = 500.0
LAG_THRESHOLD_MS = 250.0

_LOCK = Lock()
_SLOW_REQUESTS: deque = deque(maxlen=200)
_SLOW_JOBS: deque = deque(maxlen=200)
_LAG_EVENTS: deque = deque(maxlen=200)

_REQ_STATS: dict[str, dict] = defaultdict(
    lambda: {"n": 0, "sum": 0.0, "max": 0.0, "samples": deque(maxlen=100)}
)
_JOB_STATS: dict[str, dict] = defaultdict(
    lambda: {"n": 0, "sum": 0.0, "max": 0.0, "errors": 0, "missed": 0,
             "samples": deque(maxlen=100)}
)
_job_starts: dict[str, float] = {}
_current_job: dict = {"id": None, "since": 0.0}


def record_request(method: str, path: str, status: int, ms: float) -> None:
    with _LOCK:
        st = _REQ_STATS[path]
        st["n"] += 1
        st["sum"] += ms
        st["max"] = max(st["max"], ms)
        st["samples"].append(ms)
        if ms >= SLOW_REQUEST_MS:
            _SLOW_REQUESTS.append({
                "ts": time.time(), "method": method, "path": path,
                "status": status, "ms": round(ms, 1),
            })


def job_started(job_id: str) -> None:
    with _LOCK:
        _job_starts[job_id] = time.perf_counter()
        _current_job["id"] = job_id
        _current_job["since"] = time.time()


def job_finished(job_id: str, error: bool = False, missed: bool = False) -> float:
    with _LOCK:
        t0 = _job_starts.pop(job_id, None)
        ms = (time.perf_counter() - t0) * 1000.0 if t0 is not None else 0.0
        st = _JOB_STATS[job_id]
        st["n"] += 1
        st["sum"] += ms
        st["max"] = max(st["max"], ms)
        st["samples"].append(ms)
        if error:
            st["errors"] += 1
        if missed:
            st["missed"] += 1
        if ms >= SLOW_REQUEST_MS or missed or error:
            _SLOW_JOBS.append({
                "ts": time.time(), "job": job_id, "ms": round(ms, 1),
                "error": error, "missed": missed,
            })
        if _current_job["id"] == job_id:
            _current_job["id"] = None
        return ms


def current_job() -> str | None:
    return _current_job["id"]


def record_lag(lag_ms: float) -> None:
    with _LOCK:
        _LAG_EVENTS.append({
            "ts": time.time(), "ms": round(lag_ms, 1), "job": _current_job["id"],
        })


def _pct(samples, p: float) -> float | None:
    if not samples:
        return None
    s = sorted(samples)
    k = int(round((p / 100.0) * (len(s) - 1)))
    return round(s[k], 1)


def snapshot() -> dict:
    """Everything /api/perf needs: rolling stats + the recent slow/lag events."""
    with _LOCK:
        req = {
            path: {
                "n": st["n"],
                "avg_ms": round(st["sum"] / st["n"], 1) if st["n"] else 0.0,
                "p95_ms": _pct(st["samples"], 95),
                "max_ms": round(st["max"], 1),
            }
            for path, st in _REQ_STATS.items()
        }
        jobs = {
            jid: {
                "n": st["n"],
                "avg_ms": round(st["sum"] / st["n"], 1) if st["n"] else 0.0,
                "p95_ms": _pct(st["samples"], 95),
                "max_ms": round(st["max"], 1),
                "errors": st["errors"],
                "missed": st["missed"],
            }
            for jid, st in _JOB_STATS.items()
        }
        return {
            "slow_requests": list(_SLOW_REQUESTS)[-50:][::-1],
            "slow_jobs": list(_SLOW_JOBS)[-50:][::-1],
            "loop_lag": list(_LAG_EVENTS)[-50:][::-1],
            "request_stats": req,
            "job_stats": jobs,
            "current_job": dict(_current_job),
            "thresholds": {"slow_request_ms": SLOW_REQUEST_MS,
                           "lag_ms": LAG_THRESHOLD_MS},
        }


def reset() -> None:
    """Clear all buffers (tests)."""
    with _LOCK:
        _SLOW_REQUESTS.clear()
        _SLOW_JOBS.clear()
        _LAG_EVENTS.clear()
        _REQ_STATS.clear()
        _JOB_STATS.clear()
        _job_starts.clear()
        _current_job["id"] = None
