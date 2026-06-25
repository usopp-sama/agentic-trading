"""Email Service — forwards bus ALERT events to email.

The ``notify()`` funnel already emails the operationally critical pushes that
flow through it directly (approval requests, the daily digest, and watchdog
feed/kill events). This service covers the remaining alerts that are published
*only* on the bus — strategy decay and live-feed degrade/recover — so email is
a faithful replacement for Telegram's alert forwarding.

Watchdog alerts are intentionally skipped here: the watchdog already calls
``notify()`` (which emails), so re-sending its ``Topic.ALERT`` would duplicate.

With no SMTP host configured the service stays dormant — the system is fully
usable without email.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.events import Topic
from ats.core.logging import get_logger
from ats.services.email.transport import email_configured, send_email

log = get_logger("ats.email.service")

# ALERT kinds already delivered by the watchdog via notify() — don't re-email.
_SKIP_KINDS = {"watchdog"}


def format_alert(payload: dict) -> tuple[str, str]:
    """ALERT payload -> (subject, body). Pure; unit-tested without network."""
    kind = str(payload.get("kind", "alert"))
    reason = payload.get("message") or payload.get("reason") or ""
    subject = f"ALERT: {kind}"
    lines = [f"kind: {kind}"]
    if reason:
        lines.append(f"reason: {reason}")
    for key, value in payload.items():
        if key in ("kind", "message", "reason"):
            continue
        lines.append(f"{key}: {value}")
    return subject, "\n".join(lines)


class EmailService:
    name = "email"

    def __init__(self) -> None:
        self._enabled = False

    async def start(self, ctx) -> None:
        self._enabled = email_configured(get_settings())
        if not self._enabled:
            log.info("email_disabled_no_smtp")
            return
        ctx.bus.subscribe(Topic.ALERT, self._on_alert)
        log.info("email_ready")

    async def _on_alert(self, evt) -> None:
        payload = evt.payload or {}
        if str(payload.get("kind", "")) in _SKIP_KINDS:
            return
        subject, body = format_alert(payload)
        send_email(subject, body)
