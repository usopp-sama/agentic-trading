"""P4: telemetry substrate + health model + Ops Console API."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from ats.core import telemetry
from ats.core.resources import resource_sample
from ats.core.telemetry import Health, Outcome, instrument, span
from ats.server.app import create_app


def setup_function():
    telemetry.reset()


def test_span_records_ok_and_error():
    with span("svc", "op_ok"):
        pass
    with pytest.raises(ValueError):
        with span("svc", "op_bad"):
            raise ValueError("boom")
    snap = telemetry.snapshot()
    c = snap["components"]["svc"]
    assert c["calls"] == 2 and c["errors"] == 1
    assert snap["health"]["svc"] == Health.DEGRADED.value      # last outcome was ERROR


def test_instrument_decorator_sync_and_async():
    @instrument("comp")
    def work(x):
        return x * 2

    assert work(3) == 6
    assert telemetry.snapshot()["components"]["comp"]["calls"] == 1


def test_health_states():
    assert telemetry.component_health("never_seen") == Health.IDLE.value
    with span("healthy", "op"):
        pass
    assert telemetry.component_health("healthy") == Health.OK.value
    telemetry.mark("dead", Health.DOWN)
    assert telemetry.component_health("dead") == Health.DOWN.value   # explicit override


def test_resource_sample_is_honest_without_psutil():
    r = resource_sample()
    # filesystem metrics always present; psutil flag reflects availability
    assert "psutil" in r and "db_mb" in r
    if not r["psutil"]:
        assert "note" in r


def test_ops_endpoints():
    telemetry.reset()
    with span("market_data", "poll_all"):
        pass

    class _Orch:
        _started = True
        registry = {"market_data": object(), "scraper": object()}

        class scheduler:
            @staticmethod
            def get_jobs():
                return []

        def get(self, n):
            return None

    app = create_app()
    app.state.orchestrator = _Orch()
    c = TestClient(app)

    h = c.get("/api/ops/health").json()
    assert h["started"] and "market_data" in h["services"]
    assert h["health"]["market_data"] == Health.OK.value
    assert h["health"]["scraper"] == Health.IDLE.value           # registered, no activity

    t = c.get("/api/ops/telemetry").json()
    assert "market_data" in t["components"]

    r = c.get("/api/ops/resources").json()
    assert "db_mb" in r

    a = c.get("/api/ops/accounts").json()
    assert "accounts" in a


def test_ops_page_and_nav_render():
    c = TestClient(create_app())
    assert "engine room" in c.get("/ops").text
    assert ">Ops<" in c.get("/").text
