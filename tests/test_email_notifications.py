"""Email notification channel: transport, service routing, and notify() funnel.

All pure/offline — the SMTP network call is exercised via a fake ``smtplib``.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from ats.core.config import Settings
from ats.services.email import service as email_service
from ats.services.email import transport
from ats.services.email.transport import (
    build_message,
    email_configured,
    recipients,
    send_email,
)


def _cfg(**over) -> Settings:
    base = dict(
        email_smtp_host="smtp.test",
        email_smtp_port=587,
        email_smtp_user="bot@test",
        email_smtp_password="secret-app-pw",
        email_from="ATS Bot <bot@test>",
        email_to="me@test, ops@test",
        email_use_tls=True,
        email_subject_prefix="[ATS]",
    )
    base.update(over)
    return Settings(**base)


# --- configuration gating -----------------------------------------------------
def test_email_not_configured_when_unset():
    assert email_configured(Settings(email_smtp_host="", email_from="", email_to="")) is False


def test_email_configured_requires_host_from_and_to():
    assert email_configured(_cfg()) is True
    assert email_configured(_cfg(email_smtp_host="")) is False
    assert email_configured(_cfg(email_from="")) is False
    assert email_configured(_cfg(email_to="")) is False
    assert email_configured(_cfg(email_to="   ,  ")) is False


def test_recipients_parsing():
    assert recipients(_cfg(email_to="a@x, b@y ,, c@z")) == ["a@x", "b@y", "c@z"]


# --- message building ---------------------------------------------------------
def test_build_message_sets_headers_and_body():
    msg = build_message("daily digest", "equity up 1%", _cfg())
    assert msg["Subject"] == "[ATS] daily digest"
    assert msg["From"] == "ATS Bot <bot@test>"
    assert msg["To"] == "me@test, ops@test"
    assert msg.get_content().strip() == "equity up 1%"


def test_subject_strips_newlines_to_prevent_header_injection():
    msg = build_message("line one\nBcc: attacker@evil\nline two", "body", _cfg())
    subject = msg["Subject"]
    assert "\n" not in subject and "\r" not in subject
    assert "Bcc" in subject  # collapsed into the subject text, not a real header
    assert msg["Bcc"] is None


def test_build_message_blank_prefix():
    msg = build_message("hello", "b", _cfg(email_subject_prefix=""))
    assert msg["Subject"] == "hello"


# --- send_email transport -----------------------------------------------------
def test_send_email_skips_when_not_configured():
    assert send_email("s", "b", Settings(email_smtp_host="", email_from="", email_to="")) is False


class _FakeSMTP:
    instances: list["_FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.started_tls = False
        self.logged_in = None
        self.sent = None
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, msg):
        self.sent = msg


def test_send_email_starttls_login_and_send(monkeypatch):
    import smtplib

    _FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    ok = send_email("hello", "world", _cfg())

    assert ok is True
    assert len(_FakeSMTP.instances) == 1
    srv = _FakeSMTP.instances[0]
    assert (srv.host, srv.port) == ("smtp.test", 587)
    assert srv.started_tls is True
    assert srv.logged_in == ("bot@test", "secret-app-pw")
    assert srv.sent["Subject"] == "[ATS] hello"


def test_send_email_swallows_errors(monkeypatch):
    import smtplib

    def _boom(*a, **k):
        raise OSError("smtp down")

    monkeypatch.setattr(smtplib, "SMTP", _boom)
    assert send_email("s", "b", _cfg()) is False  # never raises


# --- EmailService alert routing -----------------------------------------------
def test_format_alert_renders_kind_reason_and_extras():
    subject, body = email_service.format_alert(
        {"kind": "strategy_decay", "strategy": "mean_rev", "sharpe": -0.2}
    )
    assert subject == "ALERT: strategy_decay"
    assert "kind: strategy_decay" in body
    assert "strategy: mean_rev" in body
    assert "sharpe: -0.2" in body


def test_email_service_skips_watchdog_alerts(monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(email_service, "send_email", lambda s, b: sent.append((s, b)) or True)
    svc = email_service.EmailService()

    asyncio.run(svc._on_alert(SimpleNamespace(payload={"kind": "watchdog", "reason": "stale feed"})))
    assert sent == []  # watchdog already emailed via notify()

    asyncio.run(svc._on_alert(SimpleNamespace(payload={"kind": "feed", "reason": "degraded"})))
    assert len(sent) == 1
    assert sent[0][0] == "ALERT: feed"


# --- notify() funnel ----------------------------------------------------------
def test_notify_sends_email_when_configured(monkeypatch):
    from ats.services.execution import notify as notify_mod

    captured: list[tuple[str, str]] = []
    monkeypatch.setattr(notify_mod, "email_configured", lambda s=None: True)
    monkeypatch.setattr(
        notify_mod, "send_email", lambda subject, body, settings=None: captured.append((subject, body)) or True
    )

    notify_mod.notify("APPROVAL NEEDED: BUY 10 INFY\nDecision #5")

    assert len(captured) == 1
    subject, body = captured[0]
    assert subject == "APPROVAL NEEDED: BUY 10 INFY"  # first line only
    assert "Decision #5" in body
