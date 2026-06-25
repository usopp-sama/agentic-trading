"""Notifications funnel (Email and/or Telegram, with a log fallback).

The single one-way push used for approval requests, the daily digest, and
watchdog alerts. Channels are independent and best-effort: each configured
channel is attempted, and a log line is always written so the system stays
fully functional (and auditable) offline. Email is the preferred channel;
Telegram is still supported if its token is set.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.logging import get_logger
from ats.services.email.transport import email_configured, send_email

log = get_logger("ats.notify")


def notify(message: str) -> None:
    settings = get_settings()
    delivered: list[str] = []

    if email_configured(settings):
        # Subject = first line of the message (cleaned downstream).
        subject = message.split("\n", 1)[0]
        if send_email(subject, message, settings):
            delivered.append("email")

    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:  # pragma: no cover - requires network + token
            import httpx

            httpx.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": settings.telegram_chat_id, "text": message},
                timeout=10.0,
            )
            delivered.append("telegram")
        except Exception as exc:  # noqa: BLE001
            log.warning("telegram_failed", extra={"error": str(exc)})

    # Always log: the audit trail of every push, and the sole channel when
    # nothing is configured.
    log.info("notify", extra={"message": message, "channels": delivered})
