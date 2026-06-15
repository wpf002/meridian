"""
Priority Engine
---------------
Ranks entities and signals based on ACS score, risk thresholds,
magnitude of change, and divergence patterns.

Output tiers:
  Tier 1 — Immediate (ACS >= THRESHOLD_TIER_1)
  Tier 2 — Monitor   (ACS >= THRESHOLD_TIER_2)
  Tier 3 — Log only  (ACS < THRESHOLD_TIER_2)
"""

from dataclasses import dataclass
from config.settings import PRIORITY_THRESHOLDS
from core.scoring_engine import ACSResult


@dataclass
class PrioritizedEntity:
    entity: str
    acs: float
    tier: int
    confidence: float
    flags: list[str]
    rank: int = 0


class PriorityEngine:

    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or PRIORITY_THRESHOLDS.copy()

    def assign_tier(self, acs: float) -> int:
        if acs >= self.thresholds["tier_1"]:
            return 1
        elif acs >= self.thresholds["tier_2"]:
            return 2
        return 3

    def detect_flags(self, result: ACSResult) -> list[str]:
        flags = []
        # Divergence: macro bullish but tactical bearish
        if result.mas > 0.6 and result.tas < 0.4:
            flags.append("MACRO/TACTICAL_DIVERGENCE")
        if result.mas < 0.4 and result.tas > 0.6:
            flags.append("TACTICAL/MACRO_DIVERGENCE")
        # High structural risk
        if result.srs > 0.7:
            flags.append("HIGH_STRUCTURAL_RISK")
        # Low confidence
        if result.confidence < 0.4:
            flags.append("LOW_CONFIDENCE")
        # Signal scarcity
        if result.signal_count < 3:
            flags.append("SPARSE_SIGNALS")
        return flags

    def prioritize(self, results: list[ACSResult]) -> list[PrioritizedEntity]:
        """
        Assign tiers and flags to all scored entities, then rank by ACS descending.
        """
        prioritized = []
        for result in results:
            tier = self.assign_tier(result.acs)
            flags = self.detect_flags(result)
            prioritized.append(PrioritizedEntity(
                entity=result.entity,
                acs=result.acs,
                tier=tier,
                confidence=result.confidence,
                flags=flags,
            ))

        # Rank by ACS descending
        prioritized.sort(key=lambda x: x.acs, reverse=True)
        for i, p in enumerate(prioritized):
            p.rank = i + 1

        return prioritized

    def get_tier(self, prioritized: list[PrioritizedEntity], tier: int) -> list[PrioritizedEntity]:
        return [p for p in prioritized if p.tier == tier]
