"""Persona registry: loads SME specs from YAML and fills defaults.

Each persona is a data-driven spec (no bespoke code per SME). New SMEs are
added by dropping a YAML entry; they start in ``shadow`` (weight 0) so they are
visible in transparency but cannot move money until promoted by the learning
loop (Phase 8).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ats.core.logging import get_logger

log = get_logger("ats.personas")

PERSONA_DIR = Path(__file__).resolve().parent / "personas"

_DEFAULTS = {
    "scope": "symbol",      # symbol | market
    "status": "active",     # active | shadow
    "weight": 1.0,
    "horizon": "swing",
    "max_size": 0.05,
    "family": "A",
    "inputs": [],
    "signal_weights": {},
    "system_prompt": "You are a careful financial analyst. Ground every claim in the DATA.",
}


def _normalize(spec: dict) -> dict:
    persona = {**_DEFAULTS, **spec}
    if not persona.get("signal_weights"):
        persona["signal_weights"] = {name: 1.0 for name in persona["inputs"]}
    persona["weight"] = float(persona["weight"])
    persona["max_size"] = float(persona["max_size"])
    return persona


def load_personas(directory: Path | None = None) -> list[dict]:
    directory = directory or PERSONA_DIR
    personas: list[dict] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception as exc:  # noqa: BLE001
            log.warning("persona_file_error", extra={"file": path.name, "error": str(exc)})
            continue
        for spec in data.get("personas", []):
            if "id" not in spec or spec["id"] in seen:
                continue
            seen.add(spec["id"])
            personas.append(_normalize(spec))
    log.info("personas_loaded", extra={"count": len(personas)})
    return personas


def families(personas: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in personas:
        out[p["family"]] = out.get(p["family"], 0) + 1
    return out
