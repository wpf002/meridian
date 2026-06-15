"""
Classifier
----------
Assigns asset classifications based on ACS score and decision action.

Classifications:
  CORE           — High certainty, structural dominance (ACS >= 0.75, action != RESTRICT)
  HIGH-ASYMMETRY — Strong upside with controlled risk (ACS >= 0.55)
  TACTICAL       — Timing-dependent opportunity (ACS >= 0.40)
  AVOID          — Weak structure or restricted (ACS < 0.40 or action == RESTRICT)
"""

from core.scoring_engine import ACSResult
from core.decision_logic import DecisionOutput


THRESHOLDS = {
    "CORE": 0.75,
    "HIGH-ASYMMETRY": 0.55,
    "TACTICAL": 0.40,
}


def classify(result: ACSResult, decision: DecisionOutput) -> str:
    """
    Return classification string for a single entity.
    RESTRICT override always returns AVOID.
    """
    if decision.action == "RESTRICT":
        return "AVOID"

    acs = result.acs

    if acs >= THRESHOLDS["CORE"]:
        return "CORE"
    elif acs >= THRESHOLDS["HIGH-ASYMMETRY"]:
        return "HIGH-ASYMMETRY"
    elif acs >= THRESHOLDS["TACTICAL"]:
        return "TACTICAL"
    else:
        return "AVOID"


def classify_batch(
    results: list[ACSResult],
    decisions: list[DecisionOutput],
) -> dict[str, str]:
    """
    Returns dict of entity -> classification.
    """
    decision_map = {d.entity: d for d in decisions}
    return {
        result.entity: classify(result, decision_map[result.entity])
        for result in results
        if result.entity in decision_map
    }
