"""
Simulator
---------
Runs a scenario through the full scoring pipeline and produces a portfolio
impact report:

  - Per entity: baseline ACS vs best / base / worst-case scenario ACS, the
    base-case ACS delta, and any classification change.
  - Sleeve-level drawdown: average worst-case ACS drawdown of each sleeve's
    constituents (sleeve assignment from the baseline classification).
  - Regime: the scenario's stressed regime plus a light read of the current
    regime inferred from baseline signals.

Branches are produced by scaling the scenario's overlay severity:
best = 0.5x, base = 1.0x, worst = 1.5x. Scenario branches are scored with
persist=False; the report itself is persisted as a single audited entry.
"""

import uuid
from dataclasses import dataclass, field

from config.settings import DB_PATH
from core.pipeline import MeridianPipeline
from core.traceability import TraceabilityKernel
from portfolio.constructor import PortfolioConstructor
from sandbox.scenario_builder import (
    Scenario, RISK_ON, RISK_OFF, INFLATIONARY, LIQUIDITY_CONTRACTION,
)

BRANCHES = {"best": 0.5, "base": 1.0, "worst": 1.5}


@dataclass
class EntityScenarioResult:
    entity: str
    sector: str
    sleeve: str
    baseline_acs: float
    best_acs: float
    base_acs: float
    worst_acs: float
    baseline_classification: str
    scenario_classification: str
    acs_delta: float                 # base-case minus baseline
    classification_changed: bool


@dataclass
class SleeveImpact:
    sleeve: str
    asset_count: int
    avg_base_delta: float
    worst_drawdown: float            # avg (worst_acs - baseline_acs) — most negative = most stressed


@dataclass
class ScenarioReport:
    run_id: str
    scenario_name: str
    scenario_regime: str
    current_regime: str
    entities: list[EntityScenarioResult] = field(default_factory=list)
    sleeve_impacts: list[SleeveImpact] = field(default_factory=list)
    portfolio_baseline_acs: float = 0.0
    portfolio_base_acs: float = 0.0
    downgrades: int = 0

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "scenario": self.scenario_name,
            "scenario_regime": self.scenario_regime,
            "current_regime": self.current_regime,
            "portfolio_baseline_acs": round(self.portfolio_baseline_acs, 4),
            "portfolio_base_acs": round(self.portfolio_base_acs, 4),
            "downgrades": self.downgrades,
            "entities": [vars(e) for e in self.entities],
            "sleeve_impacts": [vars(s) for s in self.sleeve_impacts],
        }


def classify_current_regime(baseline_results) -> str:
    """Infer the prevailing regime from aggregate baseline sub-scores."""
    if not baseline_results:
        return "INDETERMINATE"
    n = len(baseline_results)
    avg_tas = sum(r.tas for r in baseline_results) / n
    avg_sas = sum(r.sas for r in baseline_results) / n
    avg_mas = sum(r.mas for r in baseline_results) / n
    avg_srs = sum(r.srs for r in baseline_results) / n

    if avg_srs > 0.5:
        return RISK_OFF
    if avg_tas > 0.6 and avg_sas > 0.55:
        return RISK_ON
    if avg_mas < 0.4:
        return LIQUIDITY_CONTRACTION
    return INFLATIONARY


class Simulator:

    def __init__(self, db_path: str = None, pipeline: MeridianPipeline = None):
        self.pipeline = pipeline or MeridianPipeline(db_path or DB_PATH)
        # Derive the db from the pipeline when one is injected, so audit writes
        # land in the same database the pipeline reads from.
        self.db_path = db_path or self.pipeline.db_path
        self.constructor = PortfolioConstructor()
        self.trace = TraceabilityKernel(self.db_path)

    def run_scenario(self, scenario: Scenario, universe_data: list[dict], persist: bool = True) -> ScenarioReport:
        """
        universe_data: list of {ticker, sector, asset_class, signals(raw dicts)}.
        Returns a full ScenarioReport.
        """
        run_id = str(uuid.uuid4())
        report = ScenarioReport(
            run_id=run_id,
            scenario_name=scenario.name,
            scenario_regime=scenario.regime,
            current_regime="INDETERMINATE",
        )

        baseline_results = []
        for item in universe_data:
            ticker = item["ticker"]
            sector = item.get("sector")
            asset_class = item.get("asset_class")
            base_signals = item["signals"]

            baseline = self.pipeline.run_entity(ticker, base_signals, persist=False)
            baseline_results.append(baseline.result)
            sleeve = self.constructor._route_sleeve(baseline.classification, baseline.result) or "—"

            branch_acs = {}
            branch_class = {}
            for branch, severity in BRANCHES.items():
                overlay = scenario.overlay_signals(ticker, sector, asset_class, severity=severity)
                scan = self.pipeline.run_entity(ticker, base_signals + overlay, persist=False)
                branch_acs[branch] = scan.result.acs
                branch_class[branch] = scan.classification

            report.entities.append(EntityScenarioResult(
                entity=ticker,
                sector=sector or "—",
                sleeve=sleeve,
                baseline_acs=round(baseline.result.acs, 4),
                best_acs=round(branch_acs["best"], 4),
                base_acs=round(branch_acs["base"], 4),
                worst_acs=round(branch_acs["worst"], 4),
                baseline_classification=baseline.classification,
                scenario_classification=branch_class["base"],
                acs_delta=round(branch_acs["base"] - baseline.result.acs, 4),
                classification_changed=branch_class["base"] != baseline.classification,
            ))

        report.current_regime = classify_current_regime(baseline_results)
        report.sleeve_impacts = self._aggregate_sleeves(report.entities)
        report.downgrades = sum(
            1 for e in report.entities if e.base_acs < e.baseline_acs and e.classification_changed
        )
        if report.entities:
            report.portfolio_baseline_acs = sum(e.baseline_acs for e in report.entities) / len(report.entities)
            report.portfolio_base_acs = sum(e.base_acs for e in report.entities) / len(report.entities)

        if persist:
            self.trace.log(
                action="SCENARIO",
                run_id=run_id,
                input_data={"scenario": scenario.name, "regime": scenario.regime},
                output_data=report.to_dict(),
            )

        return report

    def _aggregate_sleeves(self, entities: list[EntityScenarioResult]) -> list[SleeveImpact]:
        by_sleeve: dict[str, list[EntityScenarioResult]] = {}
        for e in entities:
            by_sleeve.setdefault(e.sleeve, []).append(e)

        order = ["core", "growth", "defensive", "tactical", "—"]
        impacts = []
        for sleeve in sorted(by_sleeve, key=lambda s: order.index(s) if s in order else 99):
            members = by_sleeve[sleeve]
            n = len(members)
            avg_base_delta = sum(m.acs_delta for m in members) / n
            worst_drawdown = sum(m.worst_acs - m.baseline_acs for m in members) / n
            impacts.append(SleeveImpact(
                sleeve=sleeve,
                asset_count=n,
                avg_base_delta=round(avg_base_delta, 4),
                worst_drawdown=round(worst_drawdown, 4),
            ))
        return impacts
