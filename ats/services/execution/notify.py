"""Notifications (Telegram, with a log fallback).

Used for approval requests and alerts. If no Telegram token is configured it
logs instead, so the system is fully functional offline.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.logging import get_logger

log = get_logger("ats.notify")


def notify(message: str) -> None:
    settings = get_settings()
    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:  # pragma: no cover - requires network + token
            import httpx

            httpx.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": settings.telegram_chat_id, "text": message},
                timeout=10.0,
            )
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("telegram_failed", extra={"error": str(exc)})
    log.info("notify", extra={"message": message})
