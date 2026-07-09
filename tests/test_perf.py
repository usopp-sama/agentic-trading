"""P0.1: perf telemetry ring buffers + /api/perf endpoint."""

from __future__ import annotations

import time

from starlette.testclient import TestClient

from ats.core import perf
from ats.server.app import create_app


def setup_function():
    perf.reset()


def test_records_slow_request_only_over_threshold():
    perf.record_request("GET", "/fast", 200, 10.0)
    perf.record_request("GET", "/slow", 200, 800.0)
    snap = perf.snapshot()
    paths = {r["path"] for r in snap["slow_requests"]}
    assert paths == {"/slow"}                      # fast one excluded
    assert snap["request_stats"]["/fast"]["n"] == 1
    assert snap["request_stats"]["/slow"]["max_ms"] == 800.0


def test_job_timing_and_missed():
    perf.job_started("poll_all")
    time.sleep(0.01)
    ms = perf.job_finished("poll_all")
    assert ms > 0
    perf.job_finished("nightly", missed=True)      # missed job, never started
    js = perf.snapshot()["job_stats"]
    assert js["poll_all"]["n"] == 1
    assert js["nightly"]["missed"] == 1


def test_loop_lag_tagged_with_current_job():
    perf.job_started("poll_all")
    perf.record_lag(900.0)
    lag = perf.snapshot()["loop_lag"]
    assert lag and lag[0]["job"] == "poll_all" and lag[0]["ms"] == 900.0


def test_percentiles():
    for v in (100.0, 200.0, 300.0, 400.0):
        perf.record_request("GET", "/x", 200, v)
    st = perf.snapshot()["request_stats"]["/x"]
    assert st["n"] == 4 and st["avg_ms"] == 250.0 and st["p95_ms"] == 400.0


def test_perf_endpoint_and_timing_header():
    perf.reset()
    c = TestClient(create_app())
    r = c.get("/api/perf")
    assert r.status_code == 200
    body = r.json()
    assert {"slow_requests", "loop_lag", "job_stats", "request_stats"} <= body.keys()
    # the timing middleware stamps every response + records the request
    assert "x-response-time-ms" in {k.lower() for k in r.headers}
    assert perf.snapshot()["request_stats"].get("/api/perf", {}).get("n", 0) >= 1
