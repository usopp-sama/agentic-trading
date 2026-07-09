"""Tests for the optional LAN shared-token gate (ats/server/auth.py)."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ats.server.auth import TokenGateMiddleware

TOKEN = "secret-lan-token"


def _app() -> Starlette:
    async def ok(_request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", ok), Route("/api/x", ok)])
    app.add_middleware(TokenGateMiddleware, token=TOKEN)
    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_app())


def test_rejects_without_token(client):
    assert client.get("/").status_code == 401
    assert client.get("/api/x").status_code == 401


def test_rejects_wrong_token(client):
    assert client.get("/?token=nope").status_code == 401
    assert client.get("/", headers={"X-ATS-Token": "nope"}).status_code == 401


def test_accepts_query_and_sets_cookie(client):
    r = client.get("/?token=" + TOKEN)
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "").lower()
    assert "ats_token=" in sc
    assert "httponly" in sc
    assert "samesite=strict" in sc


def test_accepts_header_and_cookie(client):
    assert client.get("/api/x", headers={"X-ATS-Token": TOKEN}).status_code == 200
    client.cookies.set("ats_token", TOKEN)
    assert client.get("/").status_code == 200
