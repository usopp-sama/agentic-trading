"""Lightweight entity linking: map free text to instrument symbols.

Builds an alias table from the instruments table (company name, name without
corporate suffixes, and the symbol root) and matches them as whole words in
text. This is a pragmatic substitute for a full spaCy NER + linker; it can be
upgraded later without changing callers.
"""

from __future__ import annotations

import re

from sqlalchemy import select

from ats.core.db import session_scope
from ats.core.models import Instrument

_SUFFIXES = (" ltd", " limited", " india", " industries", " corporation", " corp")


def _aliases_for(symbol: str, name: str) -> set[str]:
    aliases: set[str] = set()
    root = symbol.split(".")[0].lstrip("^").lower()
    if len(root) >= 3:
        aliases.add(root)
    nm = name.lower().strip()
    if nm:
        aliases.add(nm)
        for suf in _SUFFIXES:
            if nm.endswith(suf):
                aliases.add(nm[: -len(suf)].strip())
        # First token if distinctive (e.g. "reliance", "infosys").
        first = nm.split()[0]
        if len(first) >= 5:
            aliases.add(first)
    return {a for a in aliases if len(a) >= 3}


class TickerMapper:
    def __init__(self) -> None:
        self._alias_to_symbol: dict[str, str] = {}
        self._sector_keywords: dict[str, str] = {}
        self._patterns: dict[str, re.Pattern] = {}
        self.reload()

    def reload(self) -> None:
        with session_scope() as s:
            rows = s.execute(select(Instrument)).scalars().all()
            instruments = [(r.symbol, r.name, r.sector) for r in rows]
        alias_map: dict[str, str] = {}
        sectors: dict[str, str] = {}
        for symbol, name, sector in instruments:
            for alias in _aliases_for(symbol, name):
                # Prefer the first symbol that claims an alias (avoid clobbering).
                alias_map.setdefault(alias, symbol)
            if sector and sector not in ("Index", "Unknown"):
                sectors.setdefault(sector.lower(), sector)
        self._alias_to_symbol = alias_map
        self._sector_keywords = sectors
        self._patterns = {
            alias: re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
            for alias in alias_map
        }

    def match(self, text: str) -> list[str]:
        if not text:
            return []
        found: set[str] = set()
        low = text.lower()
        for alias, pattern in self._patterns.items():
            if alias in low and pattern.search(text):
                found.add(self._alias_to_symbol[alias])
        return sorted(found)

    def match_sectors(self, text: str) -> list[str]:
        low = text.lower()
        return sorted({name for kw, name in self._sector_keywords.items() if kw in low})
