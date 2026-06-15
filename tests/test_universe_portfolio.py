"""Tests for Phase 2: universe seeding, universe scan, and portfolio persistence."""

import sqlite3
from pathlib import Path

import pytest

from core.scoring_engine import ACSResult
from core.decision_logic import DecisionOutput
from core.pipeline import MeridianPipeline
from portfolio.constructor import PortfolioConstructor
from meta_learning.performance_tracker import PerformanceTracker
from classification.asset_universe import AssetUniverse
from classification.seed_universe import seed_universe, SEED_ASSETS


@pytest.fixture
def db(tmp_path):
    """A fresh temp database with the schema applied."""
    db_path = str(tmp_path / "test.db")
    schema = Path("db/schema.sql").read_text()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
    return db_path


def make_result(entity, acs, srs=0.1):
    r = ACSResult(entity=entity)
    r.acs = acs
    r.mas = acs
    r.tas = acs
    r.sas = acs
    r.srs = srs
    r.confidence = 0.8
    r.signal_count = 4
    return r


def make_decision(entity, action="ESCALATE"):
    return DecisionOutput(entity=entity, acs=0.5, action=action, confidence=0.8)


def test_seed_universe_is_idempotent(db):
    added = seed_universe(db)
    assert added == len(SEED_ASSETS)
    assert seed_universe(db) == 0  # already populated → no-op
    assert len(AssetUniverse(db).tickers()) == len(SEED_ASSETS)


def test_run_universe_ranks_and_skips(db):
    pipeline = MeridianPipeline(db_path=db)
    # MSFT and TLT have signal files; ZZZZ does not.
    scans, skipped = pipeline.run_universe(["MSFT", "TLT", "ZZZZ"])

    tickers = [s.entity for s in scans]
    assert "MSFT" in tickers and "TLT" in tickers
    assert ("ZZZZ",) == tuple(t for t, _ in skipped)

    # Ranked by ACS descending — MSFT (strong) should outrank TLT (weak).
    assert scans[0].result.acs >= scans[-1].result.acs
    assert tickers.index("MSFT") < tickers.index("TLT")


def test_portfolio_persisted_and_logged(db):
    results = [
        make_result("GOOD", 0.80),
        make_result("MID", 0.60),
        make_result("BAD", 0.15),
    ]
    decisions = [
        make_decision("GOOD", "ESCALATE"),
        make_decision("MID", "MONITOR"),
        make_decision("BAD", "RESTRICT"),  # excluded from portfolio
    ]

    constructor = PortfolioConstructor()
    portfolio = constructor.construct(results, decisions)
    constructor.save(portfolio, db_path=db)

    tracker = PerformanceTracker(db)
    for a in portfolio.allocations:
        tracker.log_decision(portfolio.run_id, a.ticker, a.classification, a.acs)

    with sqlite3.connect(db) as conn:
        port_rows = conn.execute(
            "SELECT ticker FROM portfolios WHERE run_id = ?", (portfolio.run_id,)
        ).fetchall()
        outcome_rows = conn.execute(
            "SELECT ticker FROM decision_outcomes WHERE run_id = ?", (portfolio.run_id,)
        ).fetchall()

    saved = {r[0] for r in port_rows}
    assert "GOOD" in saved
    assert "BAD" not in saved  # RESTRICT → AVOID → never allocated
    assert len(outcome_rows) == len(portfolio.allocations)
