"""Tests for the watchdog state machine and Telegram protocol helpers."""

from __future__ import annotations

from ats.services.telegram.service import (
    extract_callbacks,
    format_approval,
    parse_callback,
)
from ats.services.watchdog.service import WatchdogMonitor


# --- watchdog ------------------------------------------------------------------
def _monitor() -> WatchdogMonitor:
    m = WatchdogMonitor(stale_after_s=600, kill_after_failures=3)
    m.start(now=1000.0)
    return m


def test_fresh_feed_is_healthy():
    m = _monitor()
    m.record_beat(1100.0)
    v = m.check(now=1200.0, feed_expected=True)
    assert v.healthy and not v.should_kill


def test_stale_feed_escalates_to_kill_after_n_failures():
    m = _monitor()
    m.record_beat(1000.0)
    first = m.check(now=2000.0, feed_expected=True)   # 1000s silence
    second = m.check(now=2060.0, feed_expected=True)
    third = m.check(now=2120.0, feed_expected=True)
    assert not first.healthy and not first.should_kill
    assert not second.healthy and not second.should_kill
    assert third.should_kill                          # 3rd consecutive failure
    assert third.consecutive_failures == 3


def test_recovery_resets_the_failure_count():
    m = _monitor()
    m.record_beat(1000.0)
    m.check(now=2000.0, feed_expected=True)           # failure 1
    m.record_beat(2050.0)                             # feed resumes
    healthy = m.check(now=2100.0, feed_expected=True)
    assert healthy.healthy
    relapse = m.check(now=4000.0, feed_expected=True)
    assert relapse.consecutive_failures == 1          # counts restarted


def test_closed_market_never_counts_as_failure():
    m = _monitor()
    m.record_beat(1000.0)
    v = m.check(now=99_999.0, feed_expected=False)    # overnight silence is fine
    assert v.healthy and v.consecutive_failures == 0


def test_no_baseline_yet_is_not_a_failure():
    m = WatchdogMonitor(stale_after_s=600, kill_after_failures=3)  # start() never called
    assert m.check(now=5000.0, feed_expected=True).healthy


# --- telegram protocol -------------------------------------------------------------
def test_format_approval_has_buttons_wired_to_decision():
    text, markup = format_approval(
        {"decision_id": 42, "side": "BUY", "qty": 10, "symbol": "TCS.NS", "est_value": 35000}
    )
    assert "BUY 10 TCS.NS" in text and "#42" in text
    buttons = markup["inline_keyboard"][0]
    assert buttons[0]["callback_data"] == "approve:42"
    assert buttons[1]["callback_data"] == "reject:42"


def test_parse_callback_accepts_only_known_actions():
    assert parse_callback("approve:7") == ("approve", 7)
    assert parse_callback("reject:12") == ("reject", 12)
    assert parse_callback("fire_all_engines:1") is None
    assert parse_callback("approve:notanint") is None
    assert parse_callback("") is None
    assert parse_callback("approve") is None


def test_extract_callbacks_pulls_chat_for_authorization():
    updates = [
        {"update_id": 1, "message": {"text": "hello"}},  # plain message: ignored
        {
            "update_id": 2,
            "callback_query": {
                "id": "cb9",
                "data": "approve:5",
                "message": {"message_id": 77, "chat": {"id": 12345}},
            },
        },
    ]
    callbacks = extract_callbacks(updates)
    assert len(callbacks) == 1
    cb = callbacks[0]
    assert cb["chat_id"] == "12345" and cb["data"] == "approve:5"
    assert cb["message_id"] == 77 and cb["callback_id"] == "cb9"


def test_extract_callbacks_handles_empty():
    assert extract_callbacks([]) == []
    assert extract_callbacks(None) == []
