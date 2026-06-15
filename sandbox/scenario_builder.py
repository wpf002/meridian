"""
Scenario Builder
----------------
Named macro scenarios expressed as signal overlays. A scenario describes a
shock (e.g. "Rate Shock +200bps") as a set of impacts that add signals to an
entity's baseline, optionally targeted by sector or asset class. Running a
scenario means scoring each entity with its baseline signals plus the scenario
overlay and comparing the result to baseline.

Severity scales the overlay magnitudes — the simulator uses this to produce
best / base / worst branches off a single scenario definition.
"""

from dataclasses import dataclass, field
from typing import Optional

from modules.base import make_signal

# Regime labels (mirror config.settings.REGIMES)
RISK_ON = "RISK-ON"
RISK_OFF = "RISK-OFF"
INFLATIONARY = "INFLATIONARY"
LIQUIDITY_CONTRACTION = "LIQUIDITY-CONTRACTION"


@dataclass
class ScenarioImpact:
    """One overlay signal a scenario applies, optionally targeted."""
    signal_type: str                       # macro | tactical | sentiment | structural_risk
    direction: str                         # bullish | bearish | neutral
    magnitude: float                       # base magnitude (scaled by severity)
    confidence: float
    sectors: Optional[list[str]] = None    # apply only to these sectors (None = all)
    asset_classes: Optional[list[str]] = None
    label: str = ""

    def applies_to(self, sector: Optional[str], asset_class: Optional[str]) -> bool:
        if self.sectors and sector not in self.sectors:
            return False
        if self.asset_classes and asset_class not in self.asset_classes:
            return False
        return True


@dataclass
class Scenario:
    name: str
    description: str
    regime: str
    impacts: list[ScenarioImpact] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return _slugify(self.name)

    def overlay_signals(
        self,
        entity: str,
        sector: Optional[str] = None,
        asset_class: Optional[str] = None,
        severity: float = 1.0,
    ) -> list[dict]:
        """Raw overlay signals this scenario applies to one entity at a severity."""
        out = []
        for imp in self.impacts:
            if not imp.applies_to(sector, asset_class):
                continue
            out.append(make_signal(
                entity, imp.signal_type, imp.direction,
                magnitude=min(1.0, imp.magnitude * severity),
                confidence=imp.confidence,
                source=f"scenario:{self.slug}",
                raw_payload={"scenario": self.name, "impact": imp.label or imp.signal_type},
            ))
        return out


def _slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


# --- Named scenario library -------------------------------------------------

SCENARIOS: dict[str, Scenario] = {}


def _register(scenario: Scenario) -> None:
    SCENARIOS[scenario.slug] = scenario


_register(Scenario(
    name="Rate Shock +200bps",
    description="Long-end yields jump 200bps; long-duration and rate-sensitive assets repriced.",
    regime=INFLATIONARY,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.8, 0.9, label="valuation compression"),
        ScenarioImpact("tactical", "bearish", 0.6, 0.8, sectors=["Technology"], label="growth de-rating"),
        ScenarioImpact("structural_risk", "bullish", 0.7, 0.85,
                       sectors=["Fixed Income"], label="duration risk"),
        ScenarioImpact("structural_risk", "bullish", 0.5, 0.75,
                       sectors=["Financials"], label="credit/funding stress"),
    ],
))

_register(Scenario(
    name="Equity Crash -30%",
    description="Broad risk-off drawdown; correlations spike and sentiment collapses.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("tactical", "bearish", 0.9, 0.9, label="momentum break"),
        ScenarioImpact("sentiment", "bearish", 0.8, 0.85, label="sentiment collapse"),
        ScenarioImpact("structural_risk", "bullish", 0.5, 0.8, label="systemic stress"),
    ],
))

_register(Scenario(
    name="Risk-On Rally",
    description="Liquidity-fueled melt-up; risk appetite and momentum broaden.",
    regime=RISK_ON,
    impacts=[
        ScenarioImpact("tactical", "bullish", 0.8, 0.85, label="momentum"),
        ScenarioImpact("sentiment", "bullish", 0.7, 0.8, label="risk appetite"),
    ],
))

_register(Scenario(
    name="Liquidity Contraction",
    description="QT / funding squeeze; high-beta and leveraged balance sheets pressured.",
    regime=LIQUIDITY_CONTRACTION,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.7, 0.85, label="liquidity drain"),
        ScenarioImpact("tactical", "bearish", 0.6, 0.8, sectors=["Technology"], label="high-beta unwind"),
        ScenarioImpact("structural_risk", "bullish", 0.6, 0.8,
                       sectors=["Financials"], label="funding stress"),
    ],
))


def get_scenario(name: str) -> Optional[Scenario]:
    """Look up a scenario by name (case/punctuation-insensitive)."""
    return SCENARIOS.get(_slugify(name))


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())
