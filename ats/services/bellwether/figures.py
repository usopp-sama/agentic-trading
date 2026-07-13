"""The tracked-figure registry (Bellwether P1).

A config-as-code roster of market-moving figures. Each carries a GDELT query,
a listen ``weight`` (1-5, a starting prior — P4 learns the real one), the
``market`` its words move *first* (NSE / US / both), and the ``themes`` it
tends to move (mapped to concrete tickers in P2). Deliberately data, not logic,
so it's easy to edit and unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass

_MARKETS = frozenset({"NSE", "US", "both"})


@dataclass(frozen=True)
class Figure:
    key: str                    # short slug, e.g. "modi"
    query: str                  # GDELT query phrase (quote multi-word names)
    name: str                   # display name
    weight: int                 # 1..5 listen prior
    market: str                 # NSE | US | both
    themes: tuple[str, ...]     # sectors/themes moved (mapped to symbols in P2)


# The seed roster. India-direct figures first (the cleanest signal per Phase 0:
# Modi came back with 98% daily coverage over 3 years). US/global figures carry
# a market tag so the US track (Alpaca, plan 5b) can route them later.
_FIGURES: tuple[Figure, ...] = (
    # --- India: political / policy (direct NSE link) ---
    Figure("modi", '"Narendra Modi"', "Narendra Modi", 5, "NSE",
           ("infrastructure", "defence", "psu", "railways", "capex")),
    Figure("gadkari", '"Nitin Gadkari"', "Nitin Gadkari", 4, "NSE",
           ("infrastructure", "auto", "ev", "cement", "logistics")),
    Figure("sitharaman", '"Nirmala Sitharaman"', "Nirmala Sitharaman", 5, "NSE",
           ("banking", "psu", "taxes", "capex")),
    Figure("rbi", '"Reserve Bank of India"', "RBI", 5, "NSE",
           ("banking", "nbfc", "auto", "realty")),
    Figure("goyal", '"Piyush Goyal"', "Piyush Goyal", 3, "NSE",
           ("exports", "textiles", "retail", "trade")),
    # --- US / global: first-order on US markets, second-order on NSE ---
    Figure("trump", '"Donald Trump"', "Donald Trump", 5, "both",
           ("tariffs", "it", "pharma", "metals", "risk")),
    Figure("fed", '("Federal Reserve" OR "Jerome Powell")', "US Federal Reserve", 5, "both",
           ("banking", "it", "gold", "rates")),
    Figure("musk", '"Elon Musk"', "Elon Musk", 4, "US",
           ("ev", "auto", "tech", "battery")),
    Figure("huang", '("Jensen Huang" OR "Nvidia")', "Jensen Huang / NVIDIA", 4, "US",
           ("semis", "it", "ai", "power")),
    Figure("cook", '("Tim Cook" OR "Apple")', "Tim Cook / Apple", 3, "US",
           ("tech", "electronics")),
    Figure("opec", '"OPEC"', "OPEC", 4, "both",
           ("energy", "oil", "paints", "aviation")),
)

FIGURES: dict[str, Figure] = {f.key: f for f in _FIGURES}


def all_figures() -> list[Figure]:
    return list(_FIGURES)


def get_figures(keys: list[str] | None = None) -> list[Figure]:
    """The roster, optionally filtered to ``keys`` (unknown keys are ignored)."""
    if not keys:
        return list(_FIGURES)
    want = {k.strip() for k in keys if k.strip()}
    return [f for f in _FIGURES if f.key in want]


def validate() -> None:
    """Sanity-check the registry (called by tests)."""
    seen: set[str] = set()
    for f in _FIGURES:
        assert f.key and f.key not in seen, f"duplicate/empty key: {f.key}"
        seen.add(f.key)
        assert f.query.strip(), f"{f.key}: empty query"
        assert 1 <= f.weight <= 5, f"{f.key}: weight out of range"
        assert f.market in _MARKETS, f"{f.key}: bad market {f.market!r}"
        assert f.themes, f"{f.key}: no themes"
