"""Kite one-click login: token store precedence, /kite/login, /kite/callback."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from ats.core import db
from ats.core.config import get_settings
from ats.core.models import Base
from ats.server.app import create_app
from ats.services.market_data import kite_history


@pytest.fixture()
def memdb(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool, future=True)
    Base.metadata.create_all(eng)
    fac = sessionmaker(bind=eng, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "_engine", eng)
    monkeypatch.setattr(db, "_SessionFactory", fac)
    yield eng


def test_token_store_prefers_runtime_over_env(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "kite_access_token", "env_token")
    assert kite_history.get_access_token() == "env_token"       # .env fallback
    kite_history.set_access_token("runtime_token")
    assert kite_history.get_access_token() == "runtime_token"    # DB store wins


def test_login_redirects_to_zerodha_when_creds_set(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "kite_api_key", "abc123")
    c = TestClient(create_app())
    r = c.get("/kite/login", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert "kite.zerodha.com/connect/login" in loc and "api_key=abc123" in loc


def test_login_without_creds_shows_help(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "kite_api_key", "")
    r = TestClient(create_app()).get("/kite/login")
    assert r.status_code == 200 and "ATS_KITE_API_KEY" in r.text


def test_callback_without_request_token_errors(memdb):
    r = TestClient(create_app()).get("/kite/callback")
    assert r.status_code == 200 and "No request_token" in r.text


def test_callback_exchanges_and_stores_token(memdb, monkeypatch):
    monkeypatch.setattr(kite_history, "exchange_request_token", lambda rt: "acc_" + rt)
    r = TestClient(create_app()).get("/kite/callback?request_token=REQ")
    assert r.status_code == 200 and "Historical data is ready" in r.text
    assert kite_history.get_access_token() == "acc_REQ"          # stored at runtime


def test_kite_status_shape(memdb, monkeypatch):
    monkeypatch.setattr(get_settings(), "kite_api_key", "k")
    monkeypatch.setattr(get_settings(), "kite_api_secret", "s")
    j = TestClient(create_app()).get("/api/kite/status").json()
    assert j["has_creds"] is True and j["callback"] == "/kite/callback"
