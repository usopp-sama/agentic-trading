"""Theme-based news routing for the macro (Family B) experts.

Previously *every* incoming headline nudged *all* 16 market-scope experts to
re-read and re-opine (16 Gemini calls per news burst). Most headlines are about
one thing -- crude, the rupee, the monsoon -- so the rest add cost without
signal.

This module classifies a headline into coarse macro **themes** (keyword match,
fully local) and maps each theme to the subset of experts that actually care.
A generic/unclassifiable headline falls back to a tiny always-on *core* (the
broad-picture experts) rather than the whole roster.

Pure functions -> trivially unit-tested; no I/O, no LLM.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Experts that always read, regardless of theme, so the broad regime tilt is
# never lost even on an unclassifiable headline.
CORE_PERSONAS: frozenset[str] = frozenset({"macro_economist", "global_risk"})

# Theme -> keywords (lowercased; matched on word boundaries so "oil" does not
# fire on "broil"). Tuned for Indian-market news.
THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "monetary": ("rbi", "repo", "interest rate", "rate cut", "rate hike",
                 "monetary", "liquidity", "inflation", "cpi", "wpi", "mpc"),
    "fiscal": ("budget", "fiscal deficit", "fiscal", "divestment",
               "disinvestment", "subsidy", "government spending", "gst"),
    "geopolitics": ("war", "conflict", "border", "missile", "sanction",
                    "geopolitical", "ceasefire", "military"),
    "foreign_relations": ("fii", "fpi", "foreign investor", "foreign portfolio",
                          "bilateral", "diplomatic"),
    "trade": ("tariff", "import duty", "export", "trade deal", "customs duty",
              "wto", "trade balance"),
    "fx": ("rupee", "inr", "usd/inr", "dollar", "forex", "currency",
           "exchange rate"),
    "energy": ("crude", "brent", "wti", "opec", "oil price", "natural gas",
               "petrol", "diesel", "coal", "power tariff", "fuel"),
    "commodity": ("gold", "silver", "copper", "steel", "aluminium", "aluminum",
                  "zinc", "commodity", "metal prices"),
    "regulatory": ("sebi", "regulator", "regulation", "compliance", "circular",
                   "penalty", "ban on", "norms"),
    "industrial": ("pli", "capex", "manufacturing", "factory output", "iip",
                   "infrastructure", "industrial"),
    "agri": ("monsoon", "rainfall", "kharif", "rabi", "crop", "harvest",
             "agriculture", "rural demand", "fertiliser", "fertilizer"),
    "labor": ("unemployment", "jobs", "hiring", "layoff", "wages", "labour",
              "labor", "consumption", "consumer demand"),
    "tech": ("semiconductor", "chip", "artificial intelligence", " ai ",
             "software", "digital", "startup", "data centre", "data center"),
    "climate": ("climate", "carbon", "esg", "renewable", "solar", "emission",
                "green energy", "net zero"),
    "politics": ("election", "parliament", "cabinet", "minister", "poll",
                 "policy", "reform"),
    "global": ("federal reserve", " fed ", "us rates", "treasury yield",
               "recession", "china", "europe", "global growth"),
}

# Expert -> the themes it owns. Two experts are also in CORE (always read).
PERSONA_THEMES: dict[str, frozenset[str]] = {
    "macro_economist": frozenset({"monetary", "global"}),
    "monetary_policy": frozenset({"monetary"}),
    "fiscal_policy": frozenset({"fiscal"}),
    "geopolitics": frozenset({"geopolitics"}),
    "foreign_relations": frozenset({"foreign_relations", "fx"}),
    "trade_tariffs": frozenset({"trade"}),
    "fx_analyst": frozenset({"fx", "trade"}),
    "energy_analyst": frozenset({"energy", "commodity"}),
    "regulatory_analyst": frozenset({"regulatory"}),
    "industrial_policy": frozenset({"industrial", "commodity"}),
    "agri_monsoon": frozenset({"agri"}),
    "labor_consumption": frozenset({"labor"}),
    "technology_disruption": frozenset({"tech"}),
    "climate_esg": frozenset({"climate", "energy"}),
    "global_risk": frozenset({"global", "geopolitics"}),
    "political_analyst": frozenset({"politics"}),
}


def classify_themes(text: str) -> set[str]:
    """Return the set of macro themes a headline touches (may be empty)."""
    if not text:
        return set()
    hay = f" {text.lower()} "
    hits: set[str] = set()
    for theme, kws in THEME_KEYWORDS.items():
        for kw in kws:
            if kw.startswith(" ") or kw.endswith(" "):
                if kw in hay:  # pre-spaced keywords (e.g. " ai ") match literally
                    hits.add(theme)
                    break
            elif re.search(rf"\b{re.escape(kw)}\b", hay):
                hits.add(theme)
                break
    return hits


def route_macro_personas(
    themes: Iterable[str] | None, personas: list[dict]
) -> list[dict]:
    """Pick the macro experts to run for a set of detected themes.

    Always includes the CORE experts. When no theme is detected, only CORE runs
    (the big saving). The returned list preserves the input ``personas`` order.
    """
    theme_set = set(themes or ())
    wanted: set[str] = set(CORE_PERSONAS)
    for pid, owned in PERSONA_THEMES.items():
        if owned & theme_set:
            wanted.add(pid)
    return [p for p in personas if p.get("id") in wanted]
