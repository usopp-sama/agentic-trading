"""P0.2: network polling runs off the event loop (timeout + circuit-break)."""

from __future__ import annotations

import asyncio
import time
import types

import pandas as pd
import pytest

from ats.core.config import get_settings
from ats.services.market_data.service import MarketDataService


def _minimal_service(source, symbols) -> MarketDataService:
    svc = MarketDataService.__new__(MarketDataService)   # bypass heavy __init__
    svc.source = source
    svc._symbols = symbols
    svc._bus = None
    svc._history = {}
    svc._last_price = {}
    svc._quote_ts = {}
    svc._closed_logged = False
    svc._was_degraded = False
    return svc


async def _noop():
    return None


def test_poll_all_circuit_breaks_after_consecutive_failures(monkeypatch):
    svc = _minimal_service(source=None, symbols=[f"S{i}" for i in range(20)])
    calls: list[str] = []

    async def boom(symbol):
        calls.append(symbol)
        raise RuntimeError("network down")

    monkeypatch.setattr(svc, "_poll_symbol", boom)
    monkeypatch.setattr(svc, "_check_feed_degradation", _noop)
    monkeypatch.setattr(get_settings(), "market_poll_max_consecutive_failures", 3)

    asyncio.run(svc.poll_all())
    # abandoned the cycle after 3 straight failures instead of grinding all 20
    assert len(calls) == 3


def test_slow_source_times_out_without_blocking_the_loop(monkeypatch):
    def slow_poll(symbol):
        time.sleep(2.0)                     # a hung network call
        return pd.DataFrame({"close": [1.0], "volume": [1.0]})

    svc = _minimal_service(source=types.SimpleNamespace(poll=slow_poll), symbols=["X"])
    monkeypatch.setattr(svc, "_check_feed_degradation", _noop)
    monkeypatch.setattr(get_settings(), "market_poll_timeout_s", 0.2)

    async def scenario():
        ticks = 0

        async def ticker():
            nonlocal ticks
            for _ in range(5):
                await asyncio.sleep(0.05)
                ticks += 1

        t0 = time.perf_counter()
        await asyncio.gather(svc.poll_all(), ticker())
        elapsed = time.perf_counter() - t0
        return ticks, elapsed

    ticks, elapsed = asyncio.run(scenario())
    # the loop kept ticking while the source slept in a worker thread
    assert ticks == 5
    # poll timed out (~0.2s) rather than blocking the full 2s sleep
    assert elapsed < 1.0
