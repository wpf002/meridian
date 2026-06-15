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
