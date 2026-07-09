"""QA-9: Control Room page + static assets render and serve."""

from __future__ import annotations

from starlette.testclient import TestClient

from ats.server.app import create_app


def _client():
    return TestClient(create_app())


def test_control_page_renders():
    r = _client().get("/control")
    assert r.status_code == 200
    assert "cr-root" in r.text and "Market Heatmap" in r.text
    assert 'href="/static/control_room.css"' in r.text


def test_control_assets_served():
    c = _client()
    assert c.get("/static/control_room.css").status_code == 200
    assert c.get("/static/control_room.js").status_code == 200


def test_control_in_nav():
    assert ">Control<" in _client().get("/").text
