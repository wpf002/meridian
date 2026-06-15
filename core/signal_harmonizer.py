"""
Signal Harmonizer
-----------------
Standardizes all incoming signals into a unified schema
before they enter the scoring engine.

Unified Signal Schema:
  - id
  - entity
  - timestamp
  - signal_type: macro | tactical | sentiment | structural_risk
  - direction: bullish | bearish | neutral
  - magnitude: 0.0 - 1.0
  - confidence: 0.0 - 1.0
  - source
  - raw_payload
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


VALID_SIGNAL_TYPES = {"macro", "tactical", "sentiment", "structural_risk"}
VALID_DIRECTIONS = {"bullish", "bearish", "neutral"}


class HarmonizedSignal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signal_type: str
    direction: str
    magnitude: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    raw_payload: Optional[dict] = None

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v):
        if v not in VALID_SIGNAL_TYPES:
            raise ValueError(f"signal_type must be one of {VALID_SIGNAL_TYPES}")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v not in VALID_DIRECTIONS:
            raise ValueError(f"direction must be one of {VALID_DIRECTIONS}")
        return v


class SignalHarmonizer:
    """
    Accepts raw signal inputs and normalizes them into HarmonizedSignal objects.
    Rejects malformed signals and logs failures.
    """

    def __init__(self):
        self.errors: list[dict] = []

    def harmonize(self, raw: dict) -> Optional[HarmonizedSignal]:
        """
        Accepts a raw signal dict and returns a HarmonizedSignal or None if invalid.
        """
        try:
            signal = HarmonizedSignal(**raw)
            return signal
        except Exception as e:
            self.errors.append({"raw": raw, "error": str(e)})
            return None

    def harmonize_batch(self, raws: list[dict]) -> list[HarmonizedSignal]:
        """
        Process a batch of raw signals. Returns only valid ones.
        """
        results = []
        for raw in raws:
            signal = self.harmonize(raw)
            if signal:
                results.append(signal)
        return results

    def group_by_entity(self, signals: list[HarmonizedSignal]) -> dict[str, list[HarmonizedSignal]]:
        """
        Groups harmonized signals by entity (ticker/asset).
        """
        grouped: dict[str, list[HarmonizedSignal]] = {}
        for signal in signals:
            grouped.setdefault(signal.entity, []).append(signal)
        return grouped

    def group_by_type(self, signals: list[HarmonizedSignal]) -> dict[str, list[HarmonizedSignal]]:
        """
        Groups harmonized signals by signal_type.
        """
        grouped: dict[str, list[HarmonizedSignal]] = {}
        for signal in signals:
            grouped.setdefault(signal.signal_type, []).append(signal)
        return grouped
