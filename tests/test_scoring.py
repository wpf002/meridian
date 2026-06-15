"""Tests for the ACS Scoring Engine."""

import pytest
from core.signal_harmonizer import SignalHarmonizer, HarmonizedSignal
from core.scoring_engine import ScoringEngine


def make_signal(entity, signal_type, direction, magnitude=0.8, confidence=0.9, source="test"):
    return {
        "entity": entity,
        "signal_type": signal_type,
        "direction": direction,
        "magnitude": magnitude,
        "confidence": confidence,
        "source": source,
    }


def test_harmonizer_valid_signal():
    h = SignalHarmonizer()
    raw = make_signal("AAPL", "macro", "bullish")
    signal = h.harmonize(raw)
    assert signal is not None
    assert signal.entity == "AAPL"
    assert signal.direction == "bullish"


def test_harmonizer_invalid_signal_type():
    h = SignalHarmonizer()
    raw = make_signal("AAPL", "unknown_type", "bullish")
    signal = h.harmonize(raw)
    assert signal is None
    assert len(h.errors) == 1


def test_scoring_all_bullish():
    signals = [
        HarmonizedSignal(**make_signal("NVDA", "macro", "bullish")),
        HarmonizedSignal(**make_signal("NVDA", "tactical", "bullish")),
        HarmonizedSignal(**make_signal("NVDA", "sentiment", "bullish")),
        HarmonizedSignal(**make_signal("NVDA", "structural_risk", "bearish", magnitude=0.1)),
    ]
    engine = ScoringEngine()
    result = engine.score("NVDA", signals)
    assert result.acs > 0.5
    assert result.mas > 0.5
    assert result.entity == "NVDA"


def test_scoring_high_structural_risk():
    signals = [
        HarmonizedSignal(**make_signal("XYZ", "macro", "bullish")),
        HarmonizedSignal(**make_signal("XYZ", "structural_risk", "bullish", magnitude=0.95)),
    ]
    engine = ScoringEngine()
    result = engine.score("XYZ", signals)
    assert "HIGH structural risk" in " ".join(result.notes)


def test_scoring_empty_signals():
    engine = ScoringEngine()
    result = engine.score("EMPTY", [])
    assert result.acs == 0.0
    assert result.signal_count == 0


def test_acs_clamped_to_zero():
    """ACS should never go below 0."""
    signals = [
        HarmonizedSignal(**make_signal("BAD", "structural_risk", "bullish", magnitude=1.0, confidence=1.0)),
    ]
    engine = ScoringEngine()
    result = engine.score("BAD", signals)
    assert result.acs >= 0.0
