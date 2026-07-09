"""P1.2/P1.3: sentiment backend visibility, valuation presets, refresh route."""

from __future__ import annotations

import types

from starlette.testclient import TestClient

from ats.server.app import create_app
from ats.services.analytics.service import AnalyticsService
from ats.services.nlp.service import NlpService


# --- P1.2: FinBERT/VADER backend visibility ---------------------------------

def test_sentiment_status_reports_backend():
    svc = NlpService.__new__(NlpService)
    svc.model = types.SimpleNamespace(name="finbert")
    assert svc.sentiment_status() == {"backend": "finbert"}


def test_health_includes_sentiment_backend():
    class _Nlp:
        def sentiment_status(self):
            return {"backend": "vader"}

    class _Orch:
        _started = True
        services: list = []
        def get(self, n):
            return _Nlp() if n == "nlp" else None

    app = create_app()
    app.state.orchestrator = _Orch()
    body = TestClient(app).get("/api/health").json()
    assert body["sentiment"]["backend"] == "vader"


# --- P1.3: undervalued/overvalued surface -----------------------------------

def test_valuation_presets_filter_and_rank():
    svc = AnalyticsService()
    svc.table = lambda: [                       # type: ignore[assignment]
        {"symbol": "A", "verdict": "undervalued", "mos_pct": 40},
        {"symbol": "B", "verdict": "undervalued", "mos_pct": 25},
        {"symbol": "C", "verdict": "overvalued", "mos_pct": -30},
        {"symbol": "D", "verdict": "fair", "mos_pct": 5},
    ]
    assert [r["symbol"] for r in svc.screener("undervalued")] == ["A", "B"]  # mos desc
    assert [r["symbol"] for r in svc.screener("overvalued")] == ["C"]
    assert {"undervalued", "overvalued"} <= set(svc.presets())


def test_refresh_statements_route():
    class _Fund:
        def refresh_statements(self):
            return 7

    class _Analytics:
        def run_close_pass(self):
            return 3

    class _Orch:
        _started = True
        services: list = []
        def get(self, n):
            return {"fundamentals": _Fund(), "analytics": _Analytics()}.get(n)

    app = create_app()
    app.state.orchestrator = _Orch()
    j = TestClient(app).post("/api/analytics/refresh-statements").json()
    assert j["status"] == "ok"
    assert j["statement_rows"] == 7 and j["symbols_rescored"] == 3
