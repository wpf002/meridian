"""
API Serializers
---------------
Convert the engine's dataclasses into JSON-safe dicts for the HTTP layer. The
API reuses the exact same engine objects the CLI does — these functions only
shape them for transport, never recompute anything.
"""

from core.pipeline import ScanResult
from portfolio.constructor import Portfolio


def scan_to_dict(scan: ScanResult) -> dict:
    r = scan.result
    return {
        "entity": scan.entity,
        "run_id": scan.run_id,
        "model_version": scan.model_version,
        "acs": round(r.acs, 4),
        "classification": scan.classification,
        "tier": scan.prioritized.tier,
        "action": scan.decision.action,
        "conviction": scan.confidence["conviction"],
        "components": {
            "mas": round(r.mas, 4),
            "tas": round(r.tas, 4),
            "sas": round(r.sas, 4),
            "srs": round(r.srs, 4),
        },
        "weights": r.weights_used,
        "confidence": round(r.confidence, 4),
        "signal_agreement": scan.confidence["signal_agreement"],
        "signal_count": r.signal_count,
        "flags": scan.decision.flags,
        "override_reason": scan.decision.override_reason,
        "notes": r.notes,
        "rationale": scan.rationale,
    }


def recommend_row(scan: ScanResult, rank: int) -> dict:
    return {
        "rank": rank,
        "entity": scan.entity,
        "acs": round(scan.result.acs, 4),
        "tier": scan.prioritized.tier,
        "classification": scan.classification,
        "conviction": scan.confidence["conviction"],
        "action": scan.decision.action,
        "flags": scan.decision.flags,
    }


def portfolio_to_dict(portfolio: Portfolio) -> dict:
    sleeves = {}
    for sleeve, allocs in portfolio.by_sleeve().items():
        sleeves[sleeve] = {
            "weight": round(sum(a.weight for a in allocs), 4),
            "holdings": [
                {
                    "ticker": a.ticker,
                    "weight": round(a.weight, 4),
                    "acs": round(a.acs, 4),
                    "classification": a.classification,
                }
                for a in sorted(allocs, key=lambda x: x.weight, reverse=True)
            ],
        }
    return {
        "run_id": portfolio.run_id,
        "total_weight": round(portfolio.total_weight(), 4),
        "sleeves": sleeves,
        "warnings": portfolio.warnings,
    }


def compare_to_dict(a: ScanResult, b: ScanResult) -> dict:
    def side(s: ScanResult) -> dict:
        return {
            "entity": s.entity,
            "acs": round(s.result.acs, 4),
            "classification": s.classification,
            "conviction": s.confidence["conviction"],
            "components": {
                "mas": round(s.result.mas, 4),
                "tas": round(s.result.tas, 4),
                "sas": round(s.result.sas, 4),
                "srs": round(s.result.srs, 4),
            },
        }
    sa, sb = side(a), side(b)
    return {
        "a": sa,
        "b": sb,
        "delta": {
            "acs": round(sa["acs"] - sb["acs"], 4),
            **{k: round(sa["components"][k] - sb["components"][k], 4) for k in sa["components"]},
        },
    }
