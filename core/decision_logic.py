"""
Decision Logic Layer
--------------------
Applies deterministic rules before any output reaches the user.

Rules:
  - High structural risk (SRS > 0.7) → restrict, flag
  - Macro + Tactical alignment (both > 0.65) → escalate confidence
  - Signal divergence → flag for investigation
  - ACS > TIER_1 threshold → escalate to Tier 1
"""

from dataclasses import dataclass
from core.scoring_engine import ACSResult
from core.priority_engine import PrioritizedEntity


@dataclass
class DecisionOutput:
    entity: str
    acs: float
    action: str            # ESCALATE | RESTRICT | MONITOR | LOG
    confidence: float
    override_reason: str = ""
    flags: list = None

    def __post_init__(self):
        if self.flags is None:
            self.flags = []


class DecisionLogic:

    HIGH_RISK_THRESHOLD = 0.7
    ALIGNMENT_THRESHOLD = 0.65

    def apply(self, result: ACSResult, prioritized: PrioritizedEntity) -> DecisionOutput:
        action = "LOG"
        override_reason = ""

        # Rule 1: High structural risk → RESTRICT regardless of ACS
        if result.srs > self.HIGH_RISK_THRESHOLD:
            action = "RESTRICT"
            override_reason = f"Structural risk {result.srs:.2f} exceeds threshold"

        # Rule 2: Macro + Tactical alignment → ESCALATE
        elif result.mas > self.ALIGNMENT_THRESHOLD and result.tas > self.ALIGNMENT_THRESHOLD:
            action = "ESCALATE"
            override_reason = f"Macro ({result.mas:.2f}) and Tactical ({result.tas:.2f}) aligned"

        # Rule 3: Tier 1 priority
        elif prioritized.tier == 1:
            action = "ESCALATE"

        # Rule 4: Tier 2 → MONITOR
        elif prioritized.tier == 2:
            action = "MONITOR"

        return DecisionOutput(
            entity=result.entity,
            acs=result.acs,
            action=action,
            confidence=result.confidence,
            override_reason=override_reason,
            flags=prioritized.flags.copy(),
        )

    def apply_batch(
        self,
        results: list[ACSResult],
        prioritized: list[PrioritizedEntity]
    ) -> list[DecisionOutput]:
        priority_map = {p.entity: p for p in prioritized}
        outputs = []
        for result in results:
            p = priority_map.get(result.entity)
            if p:
                outputs.append(self.apply(result, p))
        return outputs
