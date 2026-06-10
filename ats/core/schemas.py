"""Shared pydantic schemas and enums used across services.

These are the in-memory contracts (distinct from the SQLAlchemy ORM models),
used for validation of agent output, signals, and proposals.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Stance(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

    @property
    def direction(self) -> int:
        return {
            Stance.STRONG_BUY: 2,
            Stance.BUY: 1,
            Stance.NEUTRAL: 0,
            Stance.SELL: -1,
            Stance.STRONG_SELL: -2,
        }[self]


class Horizon(str, Enum):
    INTRADAY = "intraday"
    SWING = "swing"
    POSITIONAL = "positional"


class TradingMode(str, Enum):
    OFF = "OFF"
    PAPER = "PAPER"
    APPROVAL = "APPROVAL"
    AUTO = "AUTO"


class Opinion(BaseModel):
    """The structured output every SME must produce."""

    sme: str
    symbol: str
    stance: Stance = Stance.NEUTRAL
    conviction: float = Field(0.0, ge=0.0, le=1.0)
    horizon: Horizon = Horizon.SWING
    rationale: str = ""
    key_risks: list[str] = Field(default_factory=list)
    suggested_size: float = Field(0.0, ge=0.0, le=1.0)
    evidence: dict = Field(default_factory=dict)

    @field_validator("rationale")
    @classmethod
    def _trim(cls, v: str) -> str:
        return v.strip()[:2000]


class SignalModel(BaseModel):
    strategy: str
    symbol: str
    stance: Stance = Stance.NEUTRAL
    conviction: float = Field(0.0, ge=0.0, le=1.0)
    features: dict = Field(default_factory=dict)


class ProposedPosition(BaseModel):
    """CIO output: a concrete, ranked target position."""

    symbol: str
    action: str = "HOLD"  # BUY/SELL/HOLD
    target_weight: float = Field(0.0, ge=-1.0, le=1.0)
    conviction: float = Field(0.0, ge=0.0, le=1.0)
    rationale: str = ""
    contributors: dict = Field(default_factory=dict)
