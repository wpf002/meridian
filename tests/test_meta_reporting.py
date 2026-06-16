"""Tests for Phase 5: alerts, meta-learning, and reporting."""

import sqlite3
from pathlib import Path

import pytest

from core.scoring_engine import ACSResult
from core.priority_engine import PrioritizedEntity
from core.decision_logic import DecisionOutput
from outputs.alert_system import AlertSystem
from outputs import daily_brief, weekly_summary
from meta_learning.performance_tracker import PerformanceTracker
from meta_learning.weight_adjuster import WeightAdjuster
from governance.model_registry import ModelRegistry


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(Path("db/schema.sql").read_text())
    return db_path


def _result(entity, acs, srs=0.1, conf=0.8):
    r = ACSResult(entity=entity)
    r.acs, r.srs, r.confidence, r.signal_count = acs, srs, conf, 4
    r.mas = r.tas = r.sas = acs
    return r


def _prioritized(entity, acs, tier, flags=None):
    return PrioritizedEntity(entity=entity, acs=acs, tier=tier, confidence=0.8, flags=flags or [])


def _decision(entity, action="MONITOR"):
    return DecisionOutput(entity=entity, acs=0.5, action=action, confidence=0.8)


# --- Alerts -----------------------------------------------------------------

def test_alerts_fire_and_acknowledge(db):
    alerts = AlertSystem(db_path=db)
    n = alerts.check_and_fire(_result("RISKY", 0.5, srs=0.9), _prioritized("RISKY", 0.5, 2))
    assert n >= 1  # risk spike

    active = alerts.get_active()
    assert len(active) == n
    assert active[0]["severity"] == "high"

    alerts.acknowledge(active[0]["id"])
    assert len(alerts.get_active()) == n - 1


def test_tier1_breach_alert(db):
    alerts = AlertSystem(db_path=db)
    alerts.check_and_fire(_result("NVDA", 0.85), _prioritized("NVDA", 0.85, 1))
    types = {a["alert_type"] for a in alerts.get_active()}
    assert "threshold_breach" in types


# --- Performance tracker + weight adjuster ----------------------------------

def _seed_resolved_outcomes(db, n=24, accuracy=0.3):
    """Log n outcomes and resolve them at a given accuracy."""
    tracker = PerformanceTracker(db)
    correct_count = int(n * accuracy)
    for i in range(n):
        eid = tracker.log_decision(run_id=f"run{i}", ticker=f"T{i}", classification="CORE", acs=0.8)
        tracker.resolve_outcome(eid, actual_return=0.05, correct=(i < correct_count))
    return tracker


def test_resolve_ticker_marks_pending(db):
    tracker = PerformanceTracker(db)
    tracker.log_decision("r1", "NVDA", "CORE", 0.8)
    tracker.log_decision("r1", "TLT", "AVOID", 0.1)
    assert tracker.resolve_ticker("NVDA", 0.12) == 1
    # CORE with positive return -> correct
    acc = tracker.get_accuracy_by_classification()
    assert acc["CORE"]["correct"] == 1


def test_snapshot_decisions_dedupes_per_day(db):
    tracker = PerformanceTracker(db)
    items = [
        {"run_id": "r", "ticker": "NVDA", "classification": "CORE", "acs": 0.85},
        {"run_id": "r", "ticker": "AAPL", "classification": "HIGH-ASYMMETRY", "acs": 0.70},
    ]
    assert tracker.snapshot_decisions(items) == 2
    assert tracker.snapshot_decisions(items) == 0   # same day, same tickers -> no dupes
    assert tracker.count_pending() == 2


def test_resolve_due_grades_elapsed_calls(db):
    from datetime import datetime, timezone, timedelta
    tracker = PerformanceTracker(db)
    tracker.log_decision("r1", "NVDA", "CORE", 0.85)    # bullish call
    tracker.log_decision("r1", "TLT", "AVOID", 0.20)    # bearish call
    entry = datetime.now(timezone.utc)
    end = entry + timedelta(days=90)

    def prices(ticker):
        if ticker == "NVDA":
            return [(entry.isoformat(), 100.0), (end.isoformat(), 110.0)]  # +10%
        return [(entry.isoformat(), 100.0), (end.isoformat(), 95.0)]       # -5%

    # Window not elapsed yet -> nothing graded.
    assert tracker.resolve_due(prices, now=entry) == 0
    assert tracker.count_pending() == 2

    # 100 days on, both windows have elapsed and grade against real prices.
    assert tracker.resolve_due(prices, now=entry + timedelta(days=100)) == 2
    assert tracker.count_pending() == 0

    acc = tracker.get_accuracy_by_classification()
    assert acc["CORE"]["correct"] == 1    # bullish call, price rose -> correct
    assert acc["AVOID"]["correct"] == 1   # avoid call, price fell -> correct


def test_weight_adjuster_runs_a_cycle(db):
    ModelRegistry(db).register(version="1.0.0", notes="baseline")
    _seed_resolved_outcomes(db, n=24, accuracy=0.3)   # poor accuracy -> should rebalance

    adjuster = WeightAdjuster(db_path=db)
    assert adjuster.should_adjust()
    result = adjuster.run_cycle()

    assert result.adjusted
    assert result.new_version == "1.0.1"
    assert result.new_weights != result.old_weights
    assert abs(sum(result.new_weights.values()) - 1.0) < 1e-6
    # New version is now active in the registry.
    assert ModelRegistry(db).get_active()["version"] == "1.0.1"


def test_weight_adjuster_holds_when_insufficient(db):
    ModelRegistry(db).register(version="1.0.0", notes="baseline")
    _seed_resolved_outcomes(db, n=5, accuracy=0.2)
    result = WeightAdjuster(db_path=db).run_cycle()
    assert not result.adjusted
    assert "resolved" in result.reason.lower()


# --- Reporting --------------------------------------------------------------

def test_daily_brief_has_sections():
    results = [_result("NVDA", 0.85), _result("XYZ", 0.30, srs=0.9)]
    prioritized = [_prioritized("NVDA", 0.85, 1), _prioritized("XYZ", 0.30, 3)]
    decisions = [_decision("NVDA", "ESCALATE"), _decision("XYZ", "RESTRICT")]
    brief = daily_brief.generate(results, prioritized, decisions, regime="RISK-ON")

    assert "MERIDIAN DAILY BRIEF" in brief
    assert "Macro Regime: RISK-ON" in brief
    assert "TIER 1" in brief and "RISK DEVELOPMENTS" in brief
    assert "NVDA" in brief


def test_weekly_summary_detects_regime_shift_and_changes(monkeypatch, tmp_path):
    # Avoid touching the real logs/ dir.
    monkeypatch.setattr(weekly_summary, "LOG_PATH", str(tmp_path))

    class _Scan:
        def __init__(self, entity, acs, classification, action="MONITOR"):
            self.entity = entity
            self.classification = classification
            self.result = _result(entity, acs)
            self.decision = _decision(entity, action)

    scans = [_Scan("NVDA", 0.50, "TACTICAL"), _Scan("AAPL", 0.80, "CORE")]
    prior = {"regime": "RISK-ON", "classifications": {"NVDA": "CORE", "AAPL": "CORE"}}

    class _StubTracker:
        def get_accuracy_by_classification(self):
            return {}

    text = weekly_summary.generate(scans, regime="RISK-OFF", tracker=_StubTracker(), prior=prior, save=False)
    assert "REGIME SHIFT" in text
    assert "NVDA" in text and "CORE -> TACTICAL" in text
    assert "PORTFOLIO DRIFT" in text
