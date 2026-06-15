"""Tests for Phase 4: scenario builder + simulator."""

import sqlite3
from pathlib import Path

import pytest

from sandbox.scenario_builder import get_scenario, list_scenarios, _slugify
from sandbox.simulator import Simulator, classify_current_regime
from core.pipeline import MeridianPipeline


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(Path("db/schema.sql").read_text())
    return db_path


def _bullish_tech(ticker):
    return {
        "ticker": ticker, "sector": "Technology", "asset_class": "equity",
        "signals": [
            {"signal_type": "macro", "direction": "bullish", "magnitude": 0.8, "confidence": 0.9, "source": "s"},
            {"signal_type": "tactical", "direction": "bullish", "magnitude": 0.8, "confidence": 0.9, "source": "s"},
            {"signal_type": "sentiment", "direction": "bullish", "magnitude": 0.7, "confidence": 0.85, "source": "s"},
            {"signal_type": "structural_risk", "direction": "bearish", "magnitude": 0.2, "confidence": 0.8, "source": "s"},
        ],
    }


# --- Scenario builder -------------------------------------------------------

def test_scenario_lookup_is_fuzzy():
    assert get_scenario("Rate Shock +200bps") is not None
    assert get_scenario("rate shock +200bps") is get_scenario("Rate Shock +200bps")
    assert get_scenario("nonexistent") is None
    assert len(list_scenarios()) >= 4


def test_overlay_targets_by_sector():
    scenario = get_scenario("Rate Shock +200bps")
    tech = scenario.overlay_signals("NVDA", sector="Technology", asset_class="equity")
    bonds = scenario.overlay_signals("TLT", sector="Fixed Income", asset_class="etf")

    # Tech gets the growth de-rating tactical hit; Fixed Income does not.
    assert any(s["signal_type"] == "tactical" for s in tech)
    assert not any(s["signal_type"] == "tactical" for s in bonds)
    # Fixed Income gets the duration structural-risk hit.
    assert any(s["signal_type"] == "structural_risk" for s in bonds)


def test_severity_scales_magnitude():
    scenario = get_scenario("Equity Crash -30%")
    base = scenario.overlay_signals("X", severity=1.0)
    worst = scenario.overlay_signals("X", severity=1.5)
    assert worst[0]["magnitude"] >= base[0]["magnitude"]


# --- Simulator --------------------------------------------------------------

def test_adverse_scenario_lowers_acs(db):
    sim = Simulator(pipeline=MeridianPipeline(db_path=db))
    data = [_bullish_tech("NVDA"), _bullish_tech("MSFT")]
    report = sim.run_scenario(get_scenario("Equity Crash -30%"), data)

    assert report.scenario_regime == "RISK-OFF"
    assert len(report.entities) == 2
    for e in report.entities:
        assert e.base_acs < e.baseline_acs            # adverse shock lowers ACS
        assert e.worst_acs <= e.base_acs <= e.best_acs  # branch ordering
    assert report.portfolio_base_acs < report.portfolio_baseline_acs


def test_sleeve_drawdown_and_persistence(db):
    sim = Simulator(pipeline=MeridianPipeline(db_path=db))
    report = sim.run_scenario(get_scenario("Rate Shock +200bps"), [_bullish_tech("NVDA")])

    assert report.sleeve_impacts
    assert report.sleeve_impacts[0].worst_drawdown <= 0   # worst case is a drawdown

    # Persisted + audited.
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT action FROM audit_log WHERE run_id = ?", (report.run_id,)
        ).fetchall()
    assert ("SCENARIO",) in rows


def test_favorable_scenario_raises_acs(db):
    sim = Simulator(pipeline=MeridianPipeline(db_path=db))
    # A modest baseline so there's room to rise.
    data = [{
        "ticker": "AMD", "sector": "Technology", "asset_class": "equity",
        "signals": [
            {"signal_type": "tactical", "direction": "neutral", "magnitude": 0.5, "confidence": 0.7, "source": "s"},
            {"signal_type": "sentiment", "direction": "neutral", "magnitude": 0.5, "confidence": 0.7, "source": "s"},
        ],
    }]
    report = sim.run_scenario(get_scenario("Risk-On Rally"), data)
    assert report.entities[0].base_acs > report.entities[0].baseline_acs
