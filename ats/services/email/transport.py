"""SMTP transport for notifications.

A tiny, dependency-free email sender (stdlib ``smtplib`` + ``email``). It is
the preferred replacement for Telegram: alerts, the daily digest, and approval
requests are delivered over SMTP.

Design notes:
- Transport is encrypted by default — STARTTLS on port 587 (the common Gmail /
  Workspace / most-provider setup) or implicit TLS on 465 — using a verifying
  ``ssl.create_default_context()`` so the server certificate is checked.
- The SMTP password is a secret: it lives only in the environment (``repr=False``
  in settings) and is never logged.
- Messaging must never crash trading, so ``send_email`` swallows every error and
  returns a bool. With nothing configured it is a no-op (the caller falls back
  to logging).

``email_configured`` and ``build_message`` are pure and unit-tested without a
network; ``send_email`` is the thin network shell.
"""

from __future__ import annotations

import ssl
from email.message import EmailMessage

from ats.core.config import Settings, get_settings
from ats.core.logging import get_logger

log = get_logger("ats.email")


def email_configured(settings: Settings | None = None) -> bool:
    """True when enough is set to actually send (host + from + at least one to)."""
    s = settings or get_settings()
    return bool(s.email_smtp_host and s.email_from and recipients(s))


def recipients(settings: Settings | None = None) -> list[str]:
    """Parse the comma-separated ``email_to`` into a clean recipient list."""
    s = settings or get_settings()
    return [addr.strip() for addr in s.email_to.split(",") if addr.strip()]


def _clean_subject(subject: str, prefix: str) -> str:
    """Single-line, prefixed subject.

    Strips CR/LF so a multi-line ``message`` can never inject extra mail
    headers, and collapses to the first line for a tidy subject.
    """
    first_line = (subject or "").replace("\r", " ").replace("\n", " ").strip()
    first_line = first_line[:180] or "notification"
    prefix = (prefix or "").strip()
    return f"{prefix} {first_line}".strip() if prefix else first_line


def build_message(subject: str, body: str, settings: Settings | None = None) -> EmailMessage:
    """Assemble a plain-text ``EmailMessage`` (pure; no network)."""
    s = settings or get_settings()
    msg = EmailMessage()
    msg["Subject"] = _clean_subject(subject, s.email_subject_prefix)
    msg["From"] = s.email_from
    msg["To"] = ", ".join(recipients(s))
    msg.set_content(body or "")
    return msg


def send_email(subject: str, body: str, settings: Settings | None = None) -> bool:
    """Send one message. Returns True on success, False if skipped/failed.

    Never raises — alerting must not take down the trading loop.
    """
    import smtplib

    s = settings or get_settings()
    if not email_configured(s):
        return False

    msg = build_message(subject, body, s)
    context = ssl.create_default_context()
    try:  # pragma: no cover - network path
        if s.email_smtp_port == 465:
            with smtplib.SMTP_SSL(
                s.email_smtp_host, s.email_smtp_port, timeout=s.email_timeout_s, context=context
            ) as server:
                _login_and_send(server, msg, s)
        else:
            with smtplib.SMTP(s.email_smtp_host, s.email_smtp_port, timeout=s.email_timeout_s) as server:
                if s.email_use_tls:
                    server.starttls(context=context)
                _login_and_send(server, msg, s)
        return True
    except Exception as exc:  # noqa: BLE001 - messaging must never crash trading
        # Never include the password; log only the (non-secret) error string.
        log.warning("email_send_failed", extra={"error": str(exc)})
        return False


def _login_and_send(server, msg: EmailMessage, s: Settings) -> None:  # pragma: no cover - network
    if s.email_smtp_user and s.email_smtp_password:
        server.login(s.email_smtp_user, s.email_smtp_password)
    server.send_message(msg)
