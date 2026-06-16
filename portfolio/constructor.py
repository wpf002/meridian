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
from config.settings import SLEEVE_TARGETS, SLEEVE_LABELS, DB_PATH
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

    SLEEVE_ORDER = ["core", "growth", "defensive", "tactical"]

    def _route_sleeve(self, classification: str, result: ACSResult) -> str | None:
        """
        Assign one asset to exactly one sleeve.

        CORE assets anchor the Core sleeve. A non-AVOID asset that is stable but
        modest — structural risk at/below the defensive cap and ACS below the
        Growth floor — is routed to Defensive ballast instead of Tactical. The
        rest fall to Growth (HIGH-ASYMMETRY) or Tactical (TACTICAL).
        """
        if classification == "AVOID":
            return None
        if classification == "CORE":
            return "core" if result.acs >= self.constraints["min_acs_for_core_sleeve"] else "growth"

        is_low_risk = result.srs <= self.constraints["defensive_srs_max"]
        below_growth_floor = result.acs < self.constraints["min_acs_for_growth_sleeve"]
        if is_low_risk and below_growth_floor:
            return "defensive"

        if classification == "HIGH-ASYMMETRY":
            return "growth" if result.acs >= self.constraints["min_acs_for_growth_sleeve"] else "tactical"
        if classification == "TACTICAL":
            return "tactical"
        return None

    def _distribute_sleeve_targets(self, populated: list[str]) -> dict[str, float]:
        """Scale base sleeve targets over only the populated sleeves so they sum to 1.0."""
        base = {s: self.sleeve_targets.get(s, 0.0) for s in populated}
        total = sum(base.values())
        if total <= 0:
            # Fall back to equal split if targets are all zero.
            return {s: 1.0 / len(populated) for s in populated} if populated else {}
        return {s: v / total for s, v in base.items()}

    def _cap_and_normalize(self, raw: dict[str, float], cap: float) -> dict[str, float]:
        """
        Normalize weights to sum to 1.0, then water-fill against the per-asset cap:
        any asset over the cap is pinned at the cap and its excess is redistributed
        to the uncapped assets, iterating until the cap holds everywhere.
        """
        total = sum(raw.values())
        if total <= 0:
            return {}
        weights = {e: w / total for e, w in raw.items()}

        for _ in range(100):
            over = {e: w for e, w in weights.items() if w > cap + 1e-9}
            if not over:
                break
            excess = sum(w - cap for w in over.values())
            for e in over:
                weights[e] = cap
            uncapped = {e: w for e, w in weights.items() if w < cap - 1e-9}
            base = sum(uncapped.values())
            if base <= 0:
                break  # everyone is capped — residual cannot be placed
            for e in uncapped:
                weights[e] += excess * (weights[e] / base)
        return weights

    def _check_constraints(self, portfolio: "Portfolio", sector_map: dict = None) -> None:
        sleeves = portfolio.by_sleeve()

        def sleeve_name(key: str) -> str:
            return SLEEVE_LABELS.get(key, key.capitalize())

        # Total allocation (capacity shortfall when assets * cap < 1.0)
        total = portfolio.total_weight()
        if total < 0.99:
            portfolio.warnings.append(
                f"Only {total*100:.0f}% of the portfolio is invested — "
                f"{(1 - total)*100:.0f}% is left in cash. Add more names to put it to work."
            )

        # Minimum assets per populated sleeve (soft)
        min_assets = self.constraints["min_assets_per_sleeve"]
        for sleeve, allocs in sleeves.items():
            if 0 < len(allocs) < min_assets:
                plural = "name" if len(allocs) == 1 else "names"
                portfolio.warnings.append(
                    f"The {sleeve_name(sleeve)} bucket holds only {len(allocs)} {plural} — "
                    f"too few to be well diversified (aim for at least {min_assets})."
                )

        # Sector concentration (soft) — only checkable when sector data is provided
        if sector_map:
            sector_weight: dict[str, float] = {}
            for a in portfolio.allocations:
                sector = sector_map.get(a.ticker, "Unknown")
                sector_weight[sector] = sector_weight.get(sector, 0.0) + a.weight
            cap = self.constraints["max_single_sector"]
            for sector, w in sector_weight.items():
                if w > cap + 1e-9:
                    portfolio.warnings.append(
                        f"{sector} makes up {w*100:.0f}% of the portfolio — that's a lot riding on "
                        f"one sector (over the {cap*100:.0f}% guideline)."
                    )

    def construct(
        self,
        results: list[ACSResult],
        decisions: list[DecisionOutput],
        sector_map: dict = None,
    ) -> Portfolio:
        run_id = str(uuid.uuid4())
        portfolio = Portfolio(run_id=run_id)

        classifications = classify_batch(results, decisions)
        result_map = {r.entity: r for r in results}

        # 1. Route each asset to a single sleeve.
        sleeve_assets: dict[str, list[tuple]] = {}
        for entity, classification in classifications.items():
            result = result_map.get(entity)
            if result is None:
                continue
            sleeve = self._route_sleeve(classification, result)
            if sleeve is None:
                continue
            sleeve_assets.setdefault(sleeve, []).append((entity, result.acs, classification))

        if not sleeve_assets:
            return portfolio

        # 2. Redistribute empty-sleeve targets across the populated sleeves.
        sleeve_weights = self._distribute_sleeve_targets(list(sleeve_assets.keys()))

        # 3. Rank-decay weights within each sleeve.
        raw: dict[str, float] = {}
        meta: dict[str, tuple] = {}
        for sleeve, assets in sleeve_assets.items():
            assets.sort(key=lambda x: x[1], reverse=True)
            target = sleeve_weights[sleeve]
            n = len(assets)
            denom = sum(range(1, n + 1))
            for i, (ticker, acs, classification) in enumerate(assets):
                raw[ticker] = target * (n - i) / denom
                meta[ticker] = (sleeve, acs, classification)

        # 4. Apply the per-asset cap and normalize the whole book to 100%.
        final = self._cap_and_normalize(raw, self.constraints["max_single_asset"])

        for ticker, weight in final.items():
            sleeve, acs, classification = meta[ticker]
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

        # 5. Surface soft-constraint breaches.
        self._check_constraints(portfolio, sector_map)

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
