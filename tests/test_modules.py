"""
Tests for Phase 3 intelligence modules.

Deterministic modules (quant, fraud) are tested directly. LLM modules
(research, sentiment) are tested offline with an injected fake client that
returns a canned parsed object — no network calls. A final end-to-end test
feeds module-produced signals through the live MeridianPipeline scoring run,
which is the Phase 3 exit criterion.
"""

import sqlite3
from pathlib import Path

import pytest

from modules.quant_assistant import QuantAssistant
from modules.fraud_aml import FraudAMLEngine
from modules.research_copilot import ResearchCopilot, ResearchExtraction
from modules.sentiment_feed import SentimentFeed, SentimentBatch, EntitySentiment
from core.signal_harmonizer import SignalHarmonizer
from core.pipeline import MeridianPipeline


# --- Offline fake Anthropic client -----------------------------------------

class _FakeParseResponse:
    def __init__(self, parsed):
        self.parsed_output = parsed


class _FakeMessages:
    def __init__(self, parsed, calls):
        self._parsed = parsed
        self._calls = calls

    def parse(self, **kwargs):
        self._calls.append(kwargs)
        return _FakeParseResponse(self._parsed)


class FakeClient:
    """Stands in for anthropic.Anthropic — records calls, returns canned output."""
    def __init__(self, parsed):
        self.calls = []
        self.messages = _FakeMessages(parsed, self.calls)


def _all_harmonize(raws):
    """Every produced signal must pass harmonization."""
    h = SignalHarmonizer()
    signals = h.harmonize_batch(raws)
    assert len(signals) == len(raws), h.errors
    return signals


# --- Quant Assistant --------------------------------------------------------

def test_quant_uptrend_is_bullish_tactical():
    prices = [100, 101, 103, 106, 110, 115]
    sigs = QuantAssistant().to_signals("NVDA", prices)
    assert len(sigs) == 1
    s = sigs[0]
    assert s["signal_type"] == "tactical"
    assert s["direction"] == "bullish"
    assert s["raw_payload"]["trend"] == "up"
    _all_harmonize(sigs)


def test_quant_downtrend_is_bearish():
    prices = [120, 116, 110, 104, 98, 90]
    s = QuantAssistant().to_signals("XOM", prices)[0]
    assert s["direction"] == "bearish"


def test_quant_insufficient_history():
    assert QuantAssistant().to_signals("X", [100]) == []


def test_quant_backtest_scaffold():
    qa = QuantAssistant()
    history = [
        [{"signal_type": "tactical", "direction": "bearish", "magnitude": 0.6, "confidence": 0.8, "source": "t"}],
        [{"signal_type": "tactical", "direction": "bullish", "magnitude": 0.8, "confidence": 0.9, "source": "t"}],
    ]
    results = qa.backtest("NVDA", history)
    assert len(results) == 2
    assert results[1].acs > results[0].acs  # bullish set scores higher


# --- Fraud & AML ------------------------------------------------------------

def test_fraud_flags_dirty_statement():
    statement = {
        "net_income": 100, "operating_cash_flow": 20, "total_assets": 500,
        "revenue": 130, "revenue_prior": 100,
        "receivables": 80, "receivables_prior": 40,
        "insider_sells": 9, "insider_buys": 1,
    }
    eng = FraudAMLEngine()
    assessment = eng.assess("BADCO", statement)
    codes = {f["code"] for f in assessment.flags}
    assert {"HIGH_ACCRUALS", "EARNINGS_CASH_DIVERGENCE", "RECEIVABLES_DIVERGENCE", "INSIDER_SELLING"} <= codes

    s = eng.to_signals("BADCO", statement)[0]
    assert s["signal_type"] == "structural_risk"
    assert s["direction"] == "bullish"  # high risk
    _all_harmonize([s])


def test_fraud_clean_statement_is_low_risk():
    statement = {
        "net_income": 100, "operating_cash_flow": 120, "total_assets": 1000,
        "revenue": 110, "revenue_prior": 100,
        "receivables": 42, "receivables_prior": 40,
        "insider_sells": 1, "insider_buys": 3,
    }
    eng = FraudAMLEngine()
    assert eng.assess("GOODCO", statement).flags == []
    s = eng.to_signals("GOODCO", statement)[0]
    assert s["direction"] == "bearish"  # low risk


# --- Research Copilot (offline) ---------------------------------------------

def test_research_copilot_maps_extraction_to_signals():
    extraction = ResearchExtraction(
        sentiment_direction="bullish", sentiment_magnitude=0.8, sentiment_confidence=0.85,
        guidance_change="raised", accounting_flags=["Rising DSO"], summary="Strong quarter.",
    )
    copilot = ResearchCopilot(client=FakeClient(extraction))
    sigs = copilot.analyze("NVDA", "earnings transcript text ...")

    by_source = {s["source"]: s for s in sigs}
    assert by_source["research_copilot:sentiment"]["direction"] == "bullish"
    assert by_source["research_copilot:guidance"]["direction"] == "bullish"   # raised
    assert by_source["research_copilot:accounting"]["signal_type"] == "structural_risk"
    assert by_source["research_copilot:accounting"]["direction"] == "bullish"  # flagged = high risk
    assert copilot._client.calls  # the model was actually invoked
    _all_harmonize(sigs)


def test_research_copilot_clean_doc_no_risk_signal():
    extraction = ResearchExtraction(
        sentiment_direction="neutral", sentiment_magnitude=0.4, sentiment_confidence=0.6,
        guidance_change="none", accounting_flags=[], summary="In line.",
    )
    sigs = ResearchCopilot(client=FakeClient(extraction)).analyze("AAPL", "news text")
    sources = {s["source"] for s in sigs}
    assert sources == {"research_copilot:sentiment"}  # no guidance, no accounting signal


# --- Sentiment Feed (offline) -----------------------------------------------

def test_sentiment_feed_maps_batch_to_signals():
    batch = SentimentBatch(entities=[
        EntitySentiment(entity="NVDA", direction="bullish", magnitude=0.7, confidence=0.8,
                        narrative_shift=True, rationale="AI demand reaccelerating"),
        EntitySentiment(entity="TLT", direction="bearish", magnitude=0.6, confidence=0.7,
                        narrative_shift=False, rationale="Yields rising"),
    ])
    feed = SentimentFeed(client=FakeClient(batch))
    sigs = feed.analyze(["NVDA beats", "Yields climb"], entities=["NVDA", "TLT"])

    assert {s["entity"] for s in sigs} == {"NVDA", "TLT"}
    nvda = next(s for s in sigs if s["entity"] == "NVDA")
    assert nvda["direction"] == "bullish"
    assert nvda["magnitude"] > 0.7  # narrative_shift boosts magnitude
    _all_harmonize(sigs)


# --- End-to-end: module signals feed a live scoring run ---------------------

@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(Path("db/schema.sql").read_text())
    return db_path


def test_modules_feed_live_pipeline(db):
    """Phase 3 exit criterion: module outputs feed directly into a scoring run."""
    quant = QuantAssistant().to_signals("NVDA", [100, 104, 108, 113, 119, 126])
    fraud = FraudAMLEngine().to_signals("NVDA", {
        "net_income": 100, "operating_cash_flow": 130, "total_assets": 1000,
    })
    research = ResearchCopilot(client=FakeClient(ResearchExtraction(
        sentiment_direction="bullish", sentiment_magnitude=0.8, sentiment_confidence=0.85,
        guidance_change="raised", accounting_flags=[], summary="Strong.",
    ))).analyze("NVDA", "transcript")

    raw_signals = quant + fraud + research
    scan = MeridianPipeline(db_path=db).run_entity("NVDA", raw_signals)

    assert scan.result.signal_count == len(raw_signals)
    # These modules cover tactical + sentiment + structural_risk but not macro
    # (macro is 35% of the weight and comes from AURORA/manual input), so a fully
    # bullish module read tops out around 0.50 on its own.
    assert scan.result.acs >= 0.45
    assert scan.classification != "AVOID"

    # Persisted under the run.
    with sqlite3.connect(db) as conn:
        n_signals = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE entity='NVDA'"
        ).fetchone()[0]
    assert n_signals == len(raw_signals)
