"""
Confidence Engine
-----------------
Measures signal agreement across all four input domains.
Where signals converge, conviction is high.
Where they diverge, conviction is low.

Confidence is attached to every classification and allocation output.
"""

from core.scoring_engine import ACSResult


def compute_agreement(result: ACSResult) -> float:
    """
    Measures how aligned the three positive signal types are.
    Returns 0.0 (total divergence) to 1.0 (total agreement).
    Structural risk is excluded from agreement — it's a modifier, not a signal.
    """
    scores = [result.mas, result.tas, result.sas]
    if not scores:
        return 0.0

    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = variance ** 0.5

    # Convert spread to agreement score. Std-dev is in the same units as the
    # sub-scores; its theoretical max on [0, 1] is 0.5 (mass split at the
    # extremes), so std / 0.5 maps total divergence -> 0 and full agreement -> 1.
    agreement = max(0.0, 1.0 - (std / 0.5))
    return round(agreement, 4)


def conviction_label(agreement: float, acs: float) -> str:
    """
    Returns a human-readable conviction label.
    """
    if agreement >= 0.80 and acs >= 0.65:
        return "HIGH"
    elif agreement >= 0.55 or acs >= 0.50:
        return "MEDIUM"
    else:
        return "LOW"


def enrich_with_confidence(result: ACSResult) -> dict:
    """
    Returns a dict with ACS result fields plus agreement and conviction label.
    """
    agreement = compute_agreement(result)
    return {
        "entity": result.entity,
        "acs": result.acs,
        "confidence": result.confidence,
        "signal_agreement": agreement,
        "conviction": conviction_label(agreement, result.acs),
        "mas": result.mas,
        "tas": result.tas,
        "sas": result.sas,
        "srs": result.srs,
    }
