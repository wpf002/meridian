"""
Portfolio Constructor
---------------------
Converts ranked, classified assets into a weighted portfolio
allocation structured across four sleeves.

Sleeves:
  Core       — Stability and compounding. CORE assets.
  Growth     — Upside capture. HIGH-ASYMMETRY assets.
  Defensive  — Downside control. Populated manually or from low-SRS assets.
  Tactical   — Short-duration positioning. TACTICAL assets.
"""

import uuid
import sqlite3
import json
from dataclasses import dataclass, field
from config.settings import SLEEVE_TARGETS, DB_PATH
from portfolio.constraints import CONSTRAINTS
from core.scoring_engine import ACSResult
from classification.classifier import classify_batch
from core.decision_logic import DecisionOutput


@dataclass
class PortfolioAllocation:
    run_id: str
    sleeve: str
    ticker: str
    weight: float
    classification: str
    acs: float
    rationale: str = ""


@dataclass
class Portfolio:
    run_id: str
    allocations: list[PortfolioAllocation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def by_sleeve(self) -> dict[str, list[PortfolioAllocation]]:
        sleeves: dict[str, list] = {}
        for a in self.allocations:
            sleeves.setdefault(a.sleeve, []).append(a)
        return sleeves

    def total_weight(self) -> float:
        return sum(a.weight for a in self.allocations)

    def summary(self) -> dict:
        sleeves = self.by_sleeve()
        return {
            sleeve: {
                "assets": [a.ticker for a in allocs],
                "total_weight": round(sum(a.weight for a in allocs), 4),
            }
            for sleeve, allocs in sleeves.items()
        }


class PortfolioConstructor:

    def __init__(self, sleeve_targets: dict = None, constraints: dict = None):
        self.sleeve_targets = sleeve_targets or SLEEVE_TARGETS.copy()
        self.constraints = constraints or CONSTRAINTS.copy()

    def _assign_sleeve(self, classification: str) -> str | None:
        mapping = {
            "CORE": "core",
            "HIGH-ASYMMETRY": "growth",
            "TACTICAL": "tactical",
            "AVOID": None,
        }
        return mapping.get(classification)

    def construct(
        self,
        results: list[ACSResult],
        decisions: list[DecisionOutput],
    ) -> Portfolio:
        run_id = str(uuid.uuid4())
        portfolio = Portfolio(run_id=run_id)

        classifications = classify_batch(results, decisions)
        result_map = {r.entity: r for r in results}

        # Group by sleeve
        sleeve_assets: dict[str, list[tuple]] = {}
        for entity, classification in classifications.items():
            sleeve = self._assign_sleeve(classification)
            if sleeve is None:
                continue
            result = result_map.get(entity)
            if result:
                sleeve_assets.setdefault(sleeve, []).append((entity, result.acs, classification))

        # Sort each sleeve by ACS descending and assign weights
        for sleeve, assets in sleeve_assets.items():
            assets.sort(key=lambda x: x[1], reverse=True)
            sleeve_target = self.sleeve_targets.get(sleeve, 0.0)
            n = len(assets)

            for i, (ticker, acs, classification) in enumerate(assets):
                # Weight decays by rank within sleeve
                rank_weight = (n - i) / sum(range(1, n + 1))
                raw_weight = sleeve_target * rank_weight

                # Enforce max single asset constraint
                weight = min(raw_weight, self.constraints["max_single_asset"])

                portfolio.allocations.append(
                    PortfolioAllocation(
                        run_id=run_id,
                        sleeve=sleeve,
                        ticker=ticker,
                        weight=round(weight, 4),
                        classification=classification,
                        acs=round(acs, 4),
                        rationale=f"ACS {acs:.3f} | Sleeve: {sleeve} | Classification: {classification}",
                    )
                )

        # Warn if total weight deviates significantly from 1.0
        total = portfolio.total_weight()
        if not (0.85 <= total <= 1.05):
            portfolio.warnings.append(f"Total portfolio weight {total:.3f} — review allocation balance")

        return portfolio

    def save(self, portfolio: Portfolio, db_path: str = DB_PATH):
        with sqlite3.connect(db_path) as conn:
            for a in portfolio.allocations:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO portfolios
                        (id, run_id, ticker, sleeve, weight, classification, acs, rationale, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (str(uuid.uuid4()), a.run_id, a.ticker, a.sleeve, a.weight,
                     a.classification, a.acs, a.rationale),
                )
