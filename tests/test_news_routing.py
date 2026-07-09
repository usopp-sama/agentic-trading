"""Tests for theme-based macro news routing."""

from __future__ import annotations

from ats.services.agents.news_routing import (
    CORE_PERSONAS,
    classify_themes,
    route_macro_personas,
)

# Minimal stand-in for the Family B roster (id is all the router needs).
_MACRO = [
    {"id": "macro_economist"}, {"id": "monetary_policy"}, {"id": "fiscal_policy"},
    {"id": "geopolitics"}, {"id": "foreign_relations"}, {"id": "trade_tariffs"},
    {"id": "fx_analyst"}, {"id": "energy_analyst"}, {"id": "regulatory_analyst"},
    {"id": "industrial_policy"}, {"id": "agri_monsoon"}, {"id": "labor_consumption"},
    {"id": "technology_disruption"}, {"id": "climate_esg"}, {"id": "global_risk"},
    {"id": "political_analyst"},
]


def _ids(personas):
    return {p["id"] for p in personas}


def test_classify_energy_headline():
    themes = classify_themes("Brent crude jumps as OPEC trims oil output")
    assert "energy" in themes


def test_classify_fx_and_monetary():
    themes = classify_themes("Rupee slides past 86 as RBI holds repo rate")
    assert "fx" in themes
    assert "monetary" in themes


def test_classify_unrelated_is_empty():
    assert classify_themes("Local cricket team wins friendly match") == set()


def test_route_energy_includes_energy_expert_and_core():
    routed = _ids(route_macro_personas({"energy"}, _MACRO))
    assert "energy_analyst" in routed
    assert CORE_PERSONAS <= routed  # core always present


def test_route_unclassified_runs_core_only():
    routed = _ids(route_macro_personas(set(), _MACRO))
    assert routed == set(CORE_PERSONAS)


def test_route_is_strict_subset_for_single_theme():
    routed = route_macro_personas({"agri"}, _MACRO)
    # agri_monsoon + 2 core = 3, far fewer than the full 16.
    assert len(routed) < len(_MACRO)
    assert "agri_monsoon" in _ids(routed)


def test_route_preserves_roster_order():
    routed = route_macro_personas({"energy", "fx"}, _MACRO)
    ids = [p["id"] for p in routed]
    assert ids == sorted(ids, key=lambda x: [p["id"] for p in _MACRO].index(x))
