"""Runtime system state: kill switch, trading mode, and the audit log.

The kill switch and mode are persisted in ``kv_state`` so they survive
restarts. The audit log is append-only and hash-chained (each entry includes
the previous entry's hash) so tampering is detectable.
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from ats.core.config import get_settings
from ats.core.db import session_scope
from ats.core.models import AuditLog, KvState
from ats.core.logging import get_logger

log = get_logger("ats.state")

_KILL_KEY = "kill_switch"
_MODE_KEY = "trading_mode"


def _get_kv(key: str, default: dict) -> dict:
    with session_scope() as s:
        row = s.get(KvState, key)
        return dict(row.value) if row else dict(default)


def _set_kv(key: str, value: dict) -> None:
    with session_scope() as s:
        row = s.get(KvState, key)
        if row is None:
            s.add(KvState(key=key, value=value))
        else:
            row.value = value


# --- Kill switch -------------------------------------------------------------

def is_killed() -> bool:
    return bool(_get_kv(_KILL_KEY, {"engaged": False}).get("engaged", False))


def engage_kill_switch(actor: str = "system", reason: str = "") -> None:
    _set_kv(_KILL_KEY, {"engaged": True, "reason": reason})
    audit(actor, "kill_switch.engage", {"reason": reason})
    log.warning("kill_switch_engaged", extra={"reason": reason, "actor": actor})


def release_kill_switch(actor: str = "system") -> None:
    _set_kv(_KILL_KEY, {"engaged": False, "reason": ""})
    audit(actor, "kill_switch.release", {})
    log.warning("kill_switch_released", extra={"actor": actor})


# --- Trading mode ------------------------------------------------------------

def get_mode() -> str:
    default = {"mode": get_settings().trading_mode}
    return _get_kv(_MODE_KEY, default).get("mode", default["mode"])


def set_mode(mode: str, actor: str = "human") -> str:
    mode = mode.upper()
    if mode not in {"OFF", "PAPER", "APPROVAL", "AUTO"}:
        raise ValueError(f"invalid mode: {mode}")
    _set_kv(_MODE_KEY, {"mode": mode})
    audit(actor, "mode.set", {"mode": mode})
    log.warning("mode_changed", extra={"mode": mode, "actor": actor})
    return mode


def real_money_active() -> bool:
    """Real orders may flow only if gate open, mode live, and not killed."""
    settings = get_settings()
    return (
        settings.real_money_enabled
        and get_mode() in {"APPROVAL", "AUTO"}
        and not is_killed()
    )


# --- Audit log (append-only, hash-chained) ----------------------------------

def audit(actor: str, action: str, payload: dict) -> None:
    body = json.dumps(payload, default=str, sort_keys=True)
    with session_scope() as s:
        prev = s.execute(
            select(AuditLog.payload_hash).order_by(AuditLog.id.desc()).limit(1)
        ).scalar_one_or_none() or ""
        digest = hashlib.sha256((prev + actor + action + body).encode()).hexdigest()
        s.add(
            AuditLog(
                actor=actor,
                action=action,
                payload=payload,
                payload_hash=digest,
                prev_hash=prev,
            )
        )


def verify_audit_chain() -> bool:
    """Recompute the hash chain to detect tampering."""
    with session_scope() as s:
        rows = s.execute(select(AuditLog).order_by(AuditLog.id.asc())).scalars().all()
        prev = ""
        for row in rows:
            body = json.dumps(row.payload, default=str, sort_keys=True)
            digest = hashlib.sha256(
                (prev + row.actor + row.action + body).encode()
            ).hexdigest()
            if digest != row.payload_hash:
                return False
            prev = row.payload_hash
    return True
