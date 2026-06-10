"""Structured instrument profiles.

Profiles are built from sector-level theme maps plus per-instrument overrides
(business description, ETF mandate/NAV mechanics, fund style). This is a
curated, grounded substitute for ingesting annual reports/investor decks; the
shape is identical to what a document-RAG pipeline would produce, so callers
and the ``get_instrument_profile`` tool don't change when real documents are
added later.
"""

from __future__ import annotations

# Sector -> themes that, when "in favor", benefit the sector.
SECTOR_THEMES: dict[str, list[str]] = {
    "Banking & Financials": ["credit growth", "interest rates", "financial inclusion", "NPAs"],
    "IT": ["digital transformation", "AI adoption", "USD revenue", "global tech spend"],
    "Energy": ["crude oil", "energy security", "refining margins", "green energy transition"],
    "Power": ["power demand", "renewables", "grid capex", "electrification"],
    "FMCG": ["rural demand", "consumption", "input costs", "premiumization"],
    "Auto": ["vehicle demand", "EV transition", "rural recovery", "input costs"],
    "Pharma": ["US generics", "healthcare demand", "R&D pipeline", "USFDA"],
    "Healthcare": ["healthcare demand", "hospital capex", "insurance penetration"],
    "Metals": ["commodity cycle", "China demand", "infrastructure spend", "global growth"],
    "Cement": ["infrastructure spend", "housing demand", "capex cycle"],
    "Infrastructure": ["government capex", "order inflows", "execution"],
    "Telecom": ["tariff hikes", "5G adoption", "data demand", "ARPU"],
    "Consumer Durables": ["premiumization", "discretionary demand", "festive season"],
    "Retail": ["consumption", "store expansion", "discretionary demand"],
    "Realty": ["housing demand", "interest rates", "urbanization"],
    "Commodity ETF": ["safe haven", "inflation hedge", "commodity cycle", "USD"],
    "Index ETF": ["broad market", "passive flows", "Nifty beta"],
}

# Per-instrument-type templates.
_ETF_NOTE = (
    "Exchange-traded fund. Tracks an underlying basket/commodity; trades intraday "
    "with a NAV. Watch tracking error and NAV premium/discount: persistent premium "
    "suggests demand outstripping creation, discount the reverse."
)


def build_profile(symbol: str, name: str, sector: str, instrument_type: str) -> dict:
    themes = list(SECTOR_THEMES.get(sector, ["broad market"]))
    if instrument_type == "ETF":
        business = f"{name}: {_ETF_NOTE} Sector/exposure: {sector}."
        kind = "ETF"
    elif instrument_type == "INDEX":
        business = f"{name}: a market index used as a macro/regime reference, not directly tradable here."
        kind = "INDEX"
    else:
        business = (
            f"{name} operates in the {sector} sector of the Indian market. Its "
            f"fortunes are driven by themes such as {', '.join(themes[:3])}."
        )
        kind = "EQUITY"
    text = (
        f"{business} Key themes: {', '.join(themes)}. "
        f"A view favoring these themes is expressed by this instrument."
    )
    return {
        "symbol": symbol,
        "name": name,
        "sector": sector,
        "kind": kind,
        "themes": themes,
        "text": text,
    }
