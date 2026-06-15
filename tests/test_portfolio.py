"""Tests for Portfolio Constructor."""

import pytest
from core.scoring_engine import ACSResult
from core.decision_logic import DecisionOutput
from portfolio.constructor import PortfolioConstructor


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


def make_decision(entity, action="MONITOR"):
    return DecisionOutput(entity=entity, acs=0.5, action=action, confidence=0.8)


def test_portfolio_excludes_avoid():
    results = [
        make_result("GOOD", 0.80),
        make_result("BAD", 0.15),
    ]
    decisions = [
        make_decision("GOOD", "ESCALATE"),
        make_decision("BAD", "RESTRICT"),
    ]
    constructor = PortfolioConstructor()
    portfolio = constructor.construct(results, decisions)
    tickers = [a.ticker for a in portfolio.allocations]
    assert "BAD" not in tickers
    assert "GOOD" in tickers


def test_portfolio_weight_constraint():
    results = [make_result(f"ASSET{i}", 0.80) for i in range(10)]
    decisions = [make_decision(f"ASSET{i}", "ESCALATE") for i in range(10)]
    constructor = PortfolioConstructor()
    portfolio = constructor.construct(results, decisions)
    for alloc in portfolio.allocations:
        assert alloc.weight <= 0.15, f"{alloc.ticker} weight {alloc.weight} exceeds max"


def test_portfolio_has_run_id():
    results = [make_result("AAPL", 0.82)]
    decisions = [make_decision("AAPL", "ESCALATE")]
    constructor = PortfolioConstructor()
    portfolio = constructor.construct(results, decisions)
    assert portfolio.run_id is not None
    assert len(portfolio.run_id) > 0


def test_portfolio_normalizes_to_full_allocation():
    # Enough assets across sleeves that the per-asset cap can absorb 100%.
    results = [
        make_result("A", 0.85), make_result("B", 0.80), make_result("C", 0.78),
        make_result("D", 0.62), make_result("E", 0.58),
        make_result("F", 0.48), make_result("G", 0.44),
    ]
    decisions = [make_decision(r.entity, "ESCALATE") for r in results]
    portfolio = PortfolioConstructor().construct(results, decisions)
    assert abs(portfolio.total_weight() - 1.0) < 0.01
    assert all(a.weight <= 0.15 + 1e-9 for a in portfolio.allocations)


def test_defensive_sleeve_populated_from_low_risk():
    # Modest ACS + very low structural risk -> defensive ballast, not tactical.
    results = [
        make_result("STABLE", 0.48, srs=0.0),
        make_result("ANCHOR", 0.85, srs=0.0),
    ]
    decisions = [make_decision("STABLE", "MONITOR"), make_decision("ANCHOR", "ESCALATE")]
    portfolio = PortfolioConstructor().construct(results, decisions)
    by_sleeve = portfolio.by_sleeve()
    assert "STABLE" in [a.ticker for a in by_sleeve.get("defensive", [])]


def test_sector_concentration_warns():
    # 3 capped assets (3 x 0.15 = 0.45) push Technology past the 0.35 sector cap.
    results = [make_result("X", 0.80), make_result("Y", 0.78), make_result("Z", 0.76)]
    decisions = [make_decision(r.entity, "ESCALATE") for r in results]
    sector_map = {"X": "Technology", "Y": "Technology", "Z": "Technology"}
    portfolio = PortfolioConstructor().construct(results, decisions, sector_map=sector_map)
    assert any("Technology" in w for w in portfolio.warnings)
