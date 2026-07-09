"""Tests for LLM resilience: retry/backoff, recoverable mock fallback, and the
process-wide rate cap. None of these touch the network — httpx and the clock
are stubbed.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from ats.services.agents import llm_client
from ats.services.agents.llm_client import (
    HttpLLMClient,
    MockLLMClient,
    ResilientLLMClient,
    _RateLimiter,
)


class _Resp:
    def __init__(self, status: int, body: dict | None = None, headers: dict | None = None) -> None:
        self.status_code = status
        self._body = body or {}
        self.headers = headers or {}

    def json(self) -> dict:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


@pytest.fixture(autouse=True)
def _no_db_recording(monkeypatch):
    """These tests exercise ``_complete`` directly; stop the recorder from
    writing rows into the real application DB."""
    monkeypatch.setattr(llm_client, "record_llm_call", lambda **kw: None)


def _gemini_ok(text: str = "OK") -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _client(**kw) -> HttpLLMClient:
    base = dict(provider="gemini", model="m", base_url="http://x", api_key="k",
                temperature=0.1, timeout=5.0, max_retries=3, backoff_base_s=2.0,
                max_rpm=0)
    base.update(kw)
    return HttpLLMClient(**base)


# --------------------------------------------------------------------------- #
# Retry / backoff
# --------------------------------------------------------------------------- #
def test_retries_on_429_then_succeeds(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: slept.append(s))
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(429)
        return _Resp(200, _gemini_ok("hello"))

    monkeypatch.setattr(httpx, "post", fake_post)
    out = _client()._complete("sys", [{"role": "user", "content": "hi"}], json_mode=False)
    assert out == "hello"
    assert calls["n"] == 2  # one retry
    assert slept == [2.0]  # base * 2**0


def test_retry_honors_retry_after_header(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: slept.append(s))
    seq = [_Resp(429, headers={"Retry-After": "5"}), _Resp(200, _gemini_ok("ok"))]

    def fake_post(url, headers=None, json=None, timeout=None):
        return seq.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)
    out = _client()._complete("s", [{"role": "user", "content": "q"}], json_mode=False)
    assert out == "ok"
    assert slept == [5.0]  # honored Retry-After, not the 2.0 backoff


def test_network_error_retried_then_raised(monkeypatch):
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)

    def fake_post(url, headers=None, json=None, timeout=None):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(httpx.RequestError):
        _client(max_retries=2)._complete("s", [{"role": "user", "content": "q"}], json_mode=False)


def test_non_retryable_status_raises_without_retry(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: slept.append(s))

    def fake_post(url, headers=None, json=None, timeout=None):
        return _Resp(400)

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(RuntimeError):
        _client()._complete("s", [{"role": "user", "content": "q"}], json_mode=False)
    assert slept == []  # 400 is not retryable


# --------------------------------------------------------------------------- #
# Rate limiter
# --------------------------------------------------------------------------- #
def test_rate_limiter_blocks_over_cap(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(llm_client.time, "monotonic", lambda: 1000.0)
    rl = _RateLimiter(max_rpm=2)
    rl.acquire()
    rl.acquire()
    rl.acquire()  # third within the same 60s window must wait
    assert slept == [60.0]


def test_rate_limiter_disabled_when_zero(monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: slept.append(s))
    rl = _RateLimiter(max_rpm=0)
    for _ in range(10):
        rl.acquire()
    assert slept == []


# --------------------------------------------------------------------------- #
# ResilientLLMClient: degrade -> serve mock -> recover
# --------------------------------------------------------------------------- #
class _FakeReal:
    provider = "gemini"
    model = "m"

    def __init__(self) -> None:
        self.fail = False
        self.calls = 0

    @property
    def is_real(self) -> bool:
        return True

    def generate_opinion(self, persona: dict, context: dict) -> dict:
        self.calls += 1
        if self.fail:
            raise RuntimeError("429 rate limited")
        return {"stance": "buy", "conviction": 0.5, "horizon": "swing",
                "rationale": "r", "key_risks": [], "suggested_size": 0.1}

    def chat(self, system: str, messages: list[dict], json_mode: bool = False) -> str:
        if self.fail:
            raise RuntimeError("boom")
        return "real-answer"

    def health_check(self) -> tuple[bool, str]:
        return (not self.fail, "ok" if not self.fail else "down")


def test_degrades_to_mock_then_recovers_after_cooldown():
    real = _FakeReal()
    c = ResilientLLMClient(real, cooldown_s=60)
    assert c.is_real is True

    # Provider fails -> serve mock, mark degraded.
    real.fail = True
    out = c.generate_opinion({}, {})
    assert out["stance"] == "neutral"  # mock's grounded-but-empty answer
    assert c.is_real is False
    failed_calls = real.calls

    # Within cooldown: real is not even attempted.
    real.fail = False
    c.generate_opinion({}, {"signals": {"x": 0.5}})
    assert c.is_real is False
    assert real.calls == failed_calls  # real skipped during cooldown

    # Cooldown elapsed -> re-probe real, recover.
    c._degraded_until = 0.0
    out = c.generate_opinion({}, {"signals": {"x": 0.5}})
    assert out["stance"] == "buy"
    assert c.is_real is True


def test_chat_falls_back_and_status_reports_state():
    real = _FakeReal()
    c = ResilientLLMClient(real, cooldown_s=60)
    real.fail = True
    ans = c.chat("s", [{"role": "user", "content": "QUESTION: hi"}])
    assert "heuristic" in ans  # mock marker
    st = c.status()
    assert st["real"] is False and st["downgraded"] is True
    assert st["provider"] == "gemini" and st["model"] == "m"


def test_health_check_updates_live_state():
    real = _FakeReal()
    c = ResilientLLMClient(real, cooldown_s=60)
    real.fail = True
    ok, _ = c.health_check()
    assert ok is False and c.is_real is False
    real.fail = False
    ok, _ = c.health_check()
    assert ok is True and c.is_real is True


# --------------------------------------------------------------------------- #
# Factories
# --------------------------------------------------------------------------- #
def _fake_settings(**kw) -> SimpleNamespace:
    base = dict(llm_provider="gemini", llm_model="gemini-2.5-flash",
                llm_cio_model="gemini-2.5-pro", llm_base_url="http://x",
                llm_api_key="k", llm_temperature=0.1, llm_timeout_s=5.0,
                llm_num_ctx=0, llm_max_retries=3, llm_backoff_base_s=2.0,
                llm_recover_cooldown_s=180.0, llm_max_rpm=0,
                llm_max_prompt_chars=24000)
    base.update(kw)
    return SimpleNamespace(**base)


def test_build_llm_client_wraps_real_in_resilient(monkeypatch):
    monkeypatch.setattr(llm_client, "get_settings", lambda: _fake_settings())
    c = llm_client.build_llm_client("sme")
    assert isinstance(c, ResilientLLMClient)
    assert c.is_real is True


def test_build_llm_client_mock_provider(monkeypatch):
    monkeypatch.setattr(llm_client, "get_settings", lambda: _fake_settings(llm_provider="mock"))
    c = llm_client.build_llm_client("sme")
    assert isinstance(c, MockLLMClient)
