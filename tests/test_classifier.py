"""Tests for the Classification Engine."""

import pytest
from core.scoring_engine import ACSResult
from core.decision_logic import DecisionOutput
from classification.classifier import classify, classify_batch
from classification.confidence_engine import compute_agreement, conviction_label


def make_result(entity, acs, mas=0.5, tas=0.5, sas=0.5, srs=0.1):
    r = ACSResult(entity=entity)
    r.acs = acs
    r.mas = mas
    r.tas = tas
    r.sas = sas
    r.srs = srs
    r.confidence = 0.8
    r.signal_count = 4
    return r


def make_decision(entity, action="MONITOR"):
    return DecisionOutput(entity=entity, acs=0.5, action=action, confidence=0.8)


def test_classify_core():
    r = make_result("MSFT", 0.80)
    d = make_decision("MSFT", "ESCALATE")
    assert classify(r, d) == "CORE"


def test_classify_high_asymmetry():
    r = make_result("PLTR", 0.62)
    d = make_decision("PLTR", "MONITOR")
    assert classify(r, d) == "HIGH-ASYMMETRY"


def test_classify_tactical():
    r = make_result("XYZ", 0.45)
    d = make_decision("XYZ", "MONITOR")
    assert classify(r, d) == "TACTICAL"


def test_classify_avoid_low_acs():
    r = make_result("JUNK", 0.20)
    d = make_decision("JUNK", "LOG")
    assert classify(r, d) == "AVOID"


def test_classify_avoid_restricted():
    r = make_result("RISKY", 0.85)
    d = make_decision("RISKY", "RESTRICT")
    assert classify(r, d) == "AVOID"


def test_confidence_agreement_high():
    r = make_result("AAPL", 0.80, mas=0.85, tas=0.80, sas=0.82)
    agreement = compute_agreement(r)
    assert agreement > 0.80


def test_confidence_agreement_divergent():
    r = make_result("TSLA", 0.55, mas=0.9, tas=0.2, sas=0.5)
    agreement = compute_agreement(r)
    assert agreement < 0.60
