"""Optional shared-token gate for LAN deployments.

This is a *convenience* gate for a trusted home network — not a substitute for
real per-user auth. When ``ATS_DASHBOARD_TOKEN`` is set, every HTTP and
WebSocket request must present the token via ``?token=``, an ``X-ATS-Token``
header, or the ``ats_token`` cookie. A correct ``?token=`` is persisted to an
HttpOnly, SameSite=Strict cookie so the user only needs to paste it once.

For exposure beyond the LAN, front this with TLS + a VPN (see
``docs/deployment_lan.md``). The token is compared in constant time and never
logged.
"""

from __future__ import annotations

import hmac
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

_COOKIE = "ats_token"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _present_token(scope) -> tuple[str, bool]:
    """Return (token, came_via_query) extracted from the ASGI scope."""
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    qs = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
    via_query = "token" in qs and bool(qs["token"][0])
    if via_query:
        return qs["token"][0], True
    header_tok = headers.get("x-ats-token", "")
    if header_tok:
        return header_tok, False
    cookie = SimpleCookie()
    with __import__("contextlib").suppress(Exception):
        cookie.load(headers.get("cookie", ""))
    if _COOKIE in cookie:
        return cookie[_COOKIE].value, False
    return "", False


class TokenGateMiddleware:
    """Pure-ASGI middleware enforcing a shared token on http + websocket."""

    def __init__(self, app, token: str) -> None:
        self.app = app
        self._token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        provided, via_query = _present_token(scope)
        ok = bool(provided) and hmac.compare_digest(provided, self._token)

        if not ok:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                body = b"Unauthorized. Append ?token=<your token> to the URL once."
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                })
                await send({"type": "http.response.body", "body": body})
            return

        if via_query and scope["type"] == "http":
            cookie = (
                f"{_COOKIE}={self._token}; Path=/; HttpOnly; SameSite=Strict; "
                f"Max-Age={_COOKIE_MAX_AGE}"
            ).encode("latin-1")

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    message = dict(message)
                    message["headers"] = list(message.get("headers", [])) + [(b"set-cookie", cookie)]
                await send(message)

            await self.app(scope, receive, send_wrapper)
            return

        await self.app(scope, receive, send)
