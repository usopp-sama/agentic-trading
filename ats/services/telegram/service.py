"""Telegram Service — one-tap trade approvals (autonomy ladder L1).

In APPROVAL mode every staged order needs a human yes/no. This service
turns that into a phone tap: each APPROVAL_REQUEST event becomes a
Telegram message with inline **Approve / Reject** buttons; pressing one
routes straight to the ExecutionService's approve/reject (the same code
path as the dashboard, so the audit trail is identical). ALERT events
(watchdog, strategy decay, kill switch) are forwarded as plain messages.

Security posture:
- Callbacks are honored only from the configured ``telegram_chat_id`` —
  anyone else pressing a forwarded button is ignored and logged.
- The bot can approve a *staged paper/real order that already passed
  every risk gate*; it cannot place orders, change mode, or open the
  real-money gate (those stay config/dashboard-only by design).
- With no token configured, the service stays dormant — the system is
  fully usable without Telegram.

Pure helpers (``format_approval``, ``parse_callback``,
``extract_callbacks``) hold the protocol logic so it is testable
without network.
"""

from __future__ import annotations

from ats.core.config import get_settings
from ats.core.events import EventBus, Topic
from ats.core.logging import get_logger

log = get_logger("ats.telegram")

_API = "https://api.telegram.org/bot{token}/{method}"


# --- pure protocol helpers ----------------------------------------------------
def format_approval(payload: dict) -> tuple[str, dict]:
    """APPROVAL_REQUEST payload -> (message text, inline keyboard markup)."""
    decision_id = payload.get("decision_id")
    text = (
        "APPROVAL NEEDED\n"
        f"{payload.get('side', '?')} {payload.get('qty', '?')} {payload.get('symbol', '?')}\n"
        f"Est. value: Rs {payload.get('est_value', '?')}\n"
        f"Decision #{decision_id}"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"approve:{decision_id}"},
                {"text": "Reject", "callback_data": f"reject:{decision_id}"},
            ]
        ]
    }
    return text, keyboard


def parse_callback(data: str) -> tuple[str, int] | None:
    """'approve:123' -> ('approve', 123); None for anything malformed."""
    if not data or ":" not in data:
        return None
    action, _, raw_id = data.partition(":")
    if action not in ("approve", "reject"):
        return None
    try:
        return action, int(raw_id)
    except ValueError:
        return None


def extract_callbacks(updates: list[dict]) -> list[dict]:
    """Pull callback presses out of a getUpdates result.

    Returns dicts with update_id, callback_id, chat_id, message_id, data.
    """
    out: list[dict] = []
    for upd in updates or []:
        cq = upd.get("callback_query")
        if not cq:
            continue
        message = cq.get("message") or {}
        chat = message.get("chat") or {}
        out.append(
            {
                "update_id": upd.get("update_id"),
                "callback_id": cq.get("id"),
                "chat_id": str(chat.get("id", "")),
                "message_id": message.get("message_id"),
                "data": cq.get("data", ""),
            }
        )
    return out


class TelegramService:
    name = "telegram"

    def __init__(self) -> None:
        self._execution = None
        self._offset = 0
        self._enabled = False

    async def start(self, ctx) -> None:
        settings = get_settings()
        self._execution = ctx.orchestrator.get("execution")
        self._enabled = bool(settings.telegram_bot_token and settings.telegram_chat_id)
        if not self._enabled:
            log.info("telegram_disabled_no_token")
            return
        ctx.bus.subscribe(Topic.APPROVAL_REQUEST, self._on_approval_request)
        ctx.bus.subscribe(Topic.ALERT, self._on_alert)
        ctx.scheduler.add_job(
            self.poll_updates,
            "interval",
            seconds=settings.telegram_poll_interval_s,
            id="telegram_poll",
            max_instances=1,
            coalesce=True,
        )
        log.info("telegram_ready")

    # --- outbound -------------------------------------------------------------
    async def _on_approval_request(self, evt) -> None:
        text, keyboard = format_approval(evt.payload)
        self._call("sendMessage", {
            "chat_id": get_settings().telegram_chat_id,
            "text": text,
            "reply_markup": keyboard,
        })

    async def _on_alert(self, evt) -> None:
        kind = evt.payload.get("kind", "alert")
        message = evt.payload.get("message") or evt.payload.get("reason") or str(evt.payload)
        self._call("sendMessage", {
            "chat_id": get_settings().telegram_chat_id,
            "text": f"[{kind.upper()}] {message}",
        })

    # --- inbound (one-tap approvals) -------------------------------------------
    async def poll_updates(self) -> None:
        resp = self._call("getUpdates", {"offset": self._offset + 1, "timeout": 0})
        if not resp or not resp.get("ok"):
            return
        updates = resp.get("result", [])
        if updates:
            self._offset = max(u.get("update_id", 0) for u in updates)
        expected_chat = str(get_settings().telegram_chat_id)
        for cb in extract_callbacks(updates):
            if cb["chat_id"] != expected_chat:
                log.warning("telegram_callback_from_unknown_chat", extra={"chat": cb["chat_id"]})
                continue
            parsed = parse_callback(cb["data"])
            if parsed is None:
                continue
            action, decision_id = parsed
            outcome = await self._resolve(action, decision_id)
            self._call("answerCallbackQuery", {"callback_query_id": cb["callback_id"], "text": outcome})
            self._call("editMessageText", {
                "chat_id": cb["chat_id"],
                "message_id": cb["message_id"],
                "text": f"Decision #{decision_id}: {outcome} (via telegram)",
            })

    async def _resolve(self, action: str, decision_id: int) -> str:
        if self._execution is None:
            return "execution unavailable"
        if action == "approve":
            result = await self._execution.approve_decision(decision_id, actor="telegram")
        else:
            result = self._execution.reject_decision(decision_id, actor="telegram")
        return str(result.get("status", "done"))

    # --- transport ---------------------------------------------------------------
    def _call(self, method: str, payload: dict) -> dict | None:  # pragma: no cover - network
        settings = get_settings()
        if not self._enabled:
            return None
        try:
            import httpx

            resp = httpx.post(
                _API.format(token=settings.telegram_bot_token, method=method),
                json=payload,
                timeout=10.0,
            )
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - messaging must never crash trading
            log.warning("telegram_call_failed", extra={"method": method, "error": str(exc)})
            return None
