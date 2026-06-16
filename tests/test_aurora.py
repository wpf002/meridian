"""Tests for Phase 7: AURORA integration + Syntrackr overlay."""

import sqlite3
from pathlib import Path

import pytest

from integrations.aurora.schema import normalize_regime, RegimeSnapshot
from integrations.aurora import adapter
from integrations.aurora.ingestion import AuroraSignalSource
from integrations.aurora.mock import MockAuroraClient
from integrations import syntrackr
from core.signal_source import ManualSignalSource, FallbackSignalSource
from core.signal_harmonizer import SignalHarmonizer
from core.pipeline import MeridianPipeline


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(Path("db/schema.sql").read_text())
    return db_path


# --- Schema / contract ------------------------------------------------------

def test_regime_normalization():
    assert normalize_regime("RISK_ON") == "RISK-ON"
    assert normalize_regime("LIQUIDITY_CONTRACTION") == "LIQUIDITY-CONTRACTION"
    assert normalize_regime("STAGFLATIONARY") == "LIQUIDITY-CONTRACTION"
    assert normalize_regime("") == "NEUTRAL"


def test_macro_signal_from_regime():
    sig = adapter.macro_signal("NVDA", RegimeSnapshot(regime="RISK-ON", confidence=0.8))
    assert sig["signal_type"] == "macro"
    assert sig["direction"] == "bullish"
    assert sig["source"] == "aurora:regime"

    bear = adapter.macro_signal("NVDA", RegimeSnapshot(regime="RISK-OFF", confidence=0.7))
    assert bear["direction"] == "bearish"


# --- Ingestion (mock client, no network) ------------------------------------

def test_aurora_ingestion_produces_full_signal_set():
    source = AuroraSignalSource(client=MockAuroraClient(regime_label="RISK_ON", fragility=30.0))
    signals, error = source.for_ticker("AAPL")
    assert error is None

    types = {s["signal_type"] for s in signals}
    assert "macro" in types          # the gap Meridian's own modules can't fill
    assert "tactical" in types
    assert "structural_risk" in types

    # Every produced signal must harmonize.
    h = SignalHarmonizer()
    assert len(h.harmonize_batch(signals)) == len(signals), h.errors


def test_aurora_macro_lets_scan_reach_high_conviction(db):
    """With AURORA macro + bullish tactical, the deterministic path is no longer
    capped at the module-only ceiling — it reaches at least HIGH-ASYMMETRY."""
    source = AuroraSignalSource(client=MockAuroraClient(regime_label="RISK_ON", fragility=20.0))
    signals, _ = source.for_ticker("AAPL")
    scan = MeridianPipeline(db_path=db).run_entity("AAPL", signals)
    assert scan.result.mas == 1.0                       # macro now present
    assert scan.result.acs >= 0.55
    assert scan.classification in ("HIGH-ASYMMETRY", "CORE")


def test_aurora_unreachable_reports_error():
    source = AuroraSignalSource(client=MockAuroraClient(reachable=False))
    assert not source.available()
    signals, error = source.for_ticker("AAPL")
    assert signals is None
    assert "no signals" in error.lower()


# --- Manual fallback --------------------------------------------------------

def test_fallback_uses_manual_when_aurora_returns_nothing():
    aurora = AuroraSignalSource(client=MockAuroraClient(reachable=False))
    fallback = FallbackSignalSource(aurora, ManualSignalSource())
    # NVDA has a committed manual signal file.
    signals, error = fallback.for_ticker("NVDA")
    assert error is None
    assert signals and any(s["signal_type"] == "macro" for s in signals)


# --- Sentiment via injected LLM (offline) -----------------------------------

class _FakeLLM:
    """Minimal stand-in so the sentiment path runs without a real API."""
    class _M:
        def parse(self, **kw):
            from modules.sentiment_feed import SentimentBatch, EntitySentiment
            batch = SentimentBatch(entities=[EntitySentiment(
                entity="AAPL", direction="bullish", magnitude=0.7, confidence=0.8,
                narrative_shift=False, rationale="upbeat")])
            class _R:
                parsed_output = batch
            return _R()
    messages = _M()


def test_aurora_sentiment_path_with_injected_llm(db):
    source = AuroraSignalSource(client=MockAuroraClient(regime_label="RISK_ON", fragility=20.0),
                               llm_client=_FakeLLM())
    signals, _ = source.for_ticker("AAPL")
    assert any(s["signal_type"] == "sentiment" for s in signals)
    scan = MeridianPipeline(db_path=db).run_entity("AAPL", signals)
    assert scan.classification == "CORE"    # macro+tactical+sentiment+low-risk -> CORE


# --- Syntrackr overlay ------------------------------------------------------

def test_syntrackr_overlay_filters_to_universe():
    source = syntrackr.MockSyntrackrSource()
    overlay = syntrackr.build_overlay(["TLT", "NVDA"], source)  # XOM not in list
    assert "TLT" in overlay and "XOM" not in overlay
    assert overlay["TLT"].safe_to_harvest is True
    assert overlay["TLT"].unrealized_loss < 0
