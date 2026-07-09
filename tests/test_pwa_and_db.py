"""QA-10/11: PWA endpoints + SQLite WAL pragma."""

from __future__ import annotations

from starlette.testclient import TestClient

from ats.core import db
from ats.core.config import get_settings
from ats.server.app import create_app


def test_manifest_served():
    r = TestClient(create_app()).get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/manifest+json")
    assert r.json()["short_name"] == "ATS"


def test_service_worker_served_from_root():
    r = TestClient(create_app()).get("/sw.js")
    assert r.status_code == 200
    assert "application/javascript" in r.headers["content-type"]
    assert 'addEventListener("fetch"' in r.text


def test_icon_and_registration():
    c = TestClient(create_app())
    assert c.get("/static/icon.svg").status_code == 200
    assert 'rel="manifest"' in c.get("/").text


def test_sqlite_wal_pragma(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionFactory", None)
    monkeypatch.setattr(get_settings(), "db_url", f"sqlite:///{tmp_path / 'wal.db'}")
    eng = db.get_engine()
    with eng.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
    assert str(mode).lower() == "wal"
    # leave globals reset so other suites build their own engines
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionFactory", None)
