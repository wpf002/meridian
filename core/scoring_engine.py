"""
Scoring Engine
--------------
Produces the Aurum Composite Score (ACS) for each entity.

ACS = (MAS + TAS + SAS) - SRS

Where:
  MAS = Macro Alignment Score
  TAS = Tactical Alignment Score
  SAS = Sentiment Alignment Score
  SRS = Structural Risk Score (penalty)

All sub-scores are 0.0 - 1.0.
ACS is clamped to 0.0 - 1.0.
"""

from dataclasses import dataclass, field
from typing import Optional
from config.settings import SCORING_WEIGHTS
from core.signal_harmonizer import HarmonizedSignal


@dataclass
class ACSResult:
    entity: str
    mas: float = 0.0       # Macro Alignment Score
    tas: float = 0.0       # Tactical Alignment Score
    sas: float = 0.0       # Sentiment Alignment Score
    srs: float = 0.0       # Structural Risk Score
    acs: float = 0.0       # Composite Score
    confidence: float = 0.0
    signal_count: int = 0
    weights_used: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


class ScoringEngine:
    """
    Computes ACS for a given entity based on its harmonized signals.
    Weights are loaded from settings and can be overridden at runtime.
    """

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or SCORING_WEIGHTS.copy()

    def _direction_to_score(self, direction: str) -> float:
        """Convert direction label to numeric score."""
        return {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}.get(direction, 0.5)

    def _compute_sub_score(self, signals: list[HarmonizedSignal]) -> float:
        """
        Weighted average of (direction_score * magnitude * confidence)
        across a set of signals of the same type.
        Returns 0.0 if no signals.
        """
        if not signals:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for s in signals:
            score = self._direction_to_score(s.direction)
            weight = s.magnitude * s.confidence
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5  # neutral default

        return weighted_sum / total_weight

    def score(self, entity: str, signals: list[HarmonizedSignal]) -> ACSResult:
        """
        Compute the full ACS for a single entity given its signals.
        """
        result = ACSResult(entity=entity, weights_used=self.weights.copy())
        result.signal_count = len(signals)

        if not signals:
            result.notes.append("No signals provided — ACS defaulted to 0.0")
            return result

        # Group by type
        by_type: dict[str, list[HarmonizedSignal]] = {}
        for s in signals:
            by_type.setdefault(s.signal_type, []).append(s)

        # Compute sub-scores
        result.mas = self._compute_sub_score(by_type.get("macro", []))
        result.tas = self._compute_sub_score(by_type.get("tactical", []))
        result.sas = self._compute_sub_score(by_type.get("sentiment", []))
        result.srs = self._compute_sub_score(by_type.get("structural_risk", []))

        # ACS formula
        positive = (
            result.mas * self.weights["macro"]
            + result.tas * self.weights["tactical"]
            + result.sas * self.weights["sentiment"]
        )
        penalty = result.srs * self.weights["structural_risk"]
        raw_acs = positive - penalty

        result.acs = max(0.0, min(1.0, raw_acs))

        # Confidence = average confidence of all signals
        result.confidence = sum(s.confidence for s in signals) / len(signals)

        # Flag if structural risk dominates
        if result.srs > 0.7:
            result.notes.append("HIGH structural risk — output flagged for review")

        return result

    def score_batch(self, grouped: dict[str, list[HarmonizedSignal]]) -> list[ACSResult]:
        """
        Score multiple entities at once.
        grouped: dict of entity -> list of signals
        """
        return [self.score(entity, signals) for entity, signals in grouped.items()]

    def update_weights(self, new_weights: dict) -> None:
        """Update scoring weights at runtime (used by meta-learning layer)."""
        self.weights.update(new_weights)
