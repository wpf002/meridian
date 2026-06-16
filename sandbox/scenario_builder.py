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


_register(Scenario(
    name="Inflation Spike",
    description="CPI reaccelerates; the Fed stays higher-for-longer and multiples compress.",
    regime=INFLATIONARY,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.7, 0.85, label="sticky inflation"),
        ScenarioImpact("tactical", "bearish", 0.5, 0.75, sectors=["Technology"], label="multiple compression"),
        ScenarioImpact("sentiment", "bullish", 0.4, 0.7, sectors=["Energy"], label="pricing power"),
    ],
))

_register(Scenario(
    name="Recession",
    description="Growth rolls over; earnings estimates get cut and defensives outperform.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.8, 0.9, label="growth contraction"),
        ScenarioImpact("tactical", "bearish", 0.6, 0.8, label="earnings cuts"),
        ScenarioImpact("structural_risk", "bullish", 0.5, 0.8, sectors=["Financials"], label="credit losses"),
        ScenarioImpact("sentiment", "bullish", 0.3, 0.65, sectors=["Consumer Staples", "Utilities"],
                       label="defensive bid"),
    ],
))

_register(Scenario(
    name="Tech Selloff",
    description="Crowded mega-cap tech unwinds; high-multiple growth names lead the drop.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("tactical", "bearish", 0.8, 0.88, sectors=["Technology"], label="momentum unwind"),
        ScenarioImpact("sentiment", "bearish", 0.6, 0.8, sectors=["Technology"], label="narrative reversal"),
        ScenarioImpact("structural_risk", "bullish", 0.4, 0.7, sectors=["Technology"], label="positioning risk"),
    ],
))

_register(Scenario(
    name="Soft Landing",
    description="Inflation cools without a recession; the Fed eases and risk assets grind higher.",
    regime=RISK_ON,
    impacts=[
        ScenarioImpact("macro", "bullish", 0.6, 0.8, label="goldilocks backdrop"),
        ScenarioImpact("tactical", "bullish", 0.5, 0.78, label="broadening rally"),
        ScenarioImpact("sentiment", "bullish", 0.4, 0.72, label="improving confidence"),
    ],
))


_register(Scenario(
    name="Stagflation",
    description="High inflation with stalling growth — the worst of both worlds for most assets.",
    regime=INFLATIONARY,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.8, 0.9, label="stagflation"),
        ScenarioImpact("tactical", "bearish", 0.5, 0.78, label="margin squeeze"),
        ScenarioImpact("sentiment", "bullish", 0.4, 0.7, sectors=["Energy"], label="real-asset bid"),
    ],
))

_register(Scenario(
    name="Fed Rate Cuts",
    description="The Fed pivots dovish; lower rates lift long-duration and rate-sensitive names.",
    regime=RISK_ON,
    impacts=[
        ScenarioImpact("macro", "bullish", 0.7, 0.85, label="easing cycle"),
        ScenarioImpact("tactical", "bullish", 0.5, 0.78, sectors=["Technology"], label="duration tailwind"),
        ScenarioImpact("sentiment", "bullish", 0.4, 0.72, sectors=["Fixed Income"], label="bond rally"),
    ],
))

_register(Scenario(
    name="Banking Crisis",
    description="A funding scare hits banks; counterparty fear spreads across financials.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("structural_risk", "bullish", 0.8, 0.9, sectors=["Financials"], label="counterparty risk"),
        ScenarioImpact("tactical", "bearish", 0.7, 0.85, sectors=["Financials"], label="deposit flight"),
        ScenarioImpact("sentiment", "bearish", 0.6, 0.8, label="contagion fear"),
    ],
))

_register(Scenario(
    name="Oil Shock",
    description="Crude spikes on a supply disruption; energy gains, everyone else pays at the pump.",
    regime=INFLATIONARY,
    impacts=[
        ScenarioImpact("sentiment", "bullish", 0.7, 0.85, sectors=["Energy"], label="energy windfall"),
        ScenarioImpact("macro", "bearish", 0.6, 0.82, label="input-cost shock"),
        ScenarioImpact("tactical", "bearish", 0.5, 0.75, sectors=["Technology"], label="demand drag"),
    ],
))

_register(Scenario(
    name="Dollar Surge",
    description="A soaring dollar squeezes multinationals and tightens global financial conditions.",
    regime=LIQUIDITY_CONTRACTION,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.6, 0.82, label="tighter conditions"),
        ScenarioImpact("tactical", "bearish", 0.5, 0.76, sectors=["Technology"], label="FX headwind"),
        ScenarioImpact("structural_risk", "bullish", 0.4, 0.72, label="funding stress"),
    ],
))

_register(Scenario(
    name="AI Capex Bust",
    description="The AI spending boom stalls; semis and hyperscalers de-rate hard.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("tactical", "bearish", 0.85, 0.9, sectors=["Technology"], label="capex unwind"),
        ScenarioImpact("sentiment", "bearish", 0.7, 0.82, sectors=["Technology"], label="hype reversal"),
        ScenarioImpact("structural_risk", "bullish", 0.5, 0.75, sectors=["Technology"], label="overbuild risk"),
    ],
))

_register(Scenario(
    name="Geopolitical Shock",
    description="A sudden conflict drives a flight to safety; energy and defense hold up.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("sentiment", "bearish", 0.7, 0.85, label="risk aversion"),
        ScenarioImpact("tactical", "bearish", 0.6, 0.8, label="broad de-risking"),
        ScenarioImpact("sentiment", "bullish", 0.4, 0.72, sectors=["Energy"], label="supply premium"),
    ],
))

_register(Scenario(
    name="Deflation Scare",
    description="Demand collapses and prices fall; cash and long bonds win, equities don't.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.8, 0.88, label="demand collapse"),
        ScenarioImpact("tactical", "bearish", 0.6, 0.8, label="pricing power loss"),
        ScenarioImpact("sentiment", "bullish", 0.4, 0.7, sectors=["Fixed Income"], label="duration bid"),
    ],
))

_register(Scenario(
    name="Consumer Slowdown",
    description="The consumer taps out; discretionary spending and retail-exposed names soften.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("tactical", "bearish", 0.6, 0.82, sectors=["Consumer Discretionary"], label="spending pullback"),
        ScenarioImpact("macro", "bearish", 0.5, 0.78, label="growth drag"),
        ScenarioImpact("sentiment", "bullish", 0.3, 0.68, sectors=["Consumer Staples"], label="defensive shift"),
    ],
))

_register(Scenario(
    name="Earnings Recession",
    description="Profits fall for several quarters even as the economy limps along.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("tactical", "bearish", 0.7, 0.85, label="earnings cuts"),
        ScenarioImpact("sentiment", "bearish", 0.5, 0.78, label="guidance misses"),
    ],
))

_register(Scenario(
    name="Commodity Boom",
    description="A broad commodity upcycle lifts energy and materials, pressures importers.",
    regime=INFLATIONARY,
    impacts=[
        ScenarioImpact("sentiment", "bullish", 0.7, 0.85, sectors=["Energy", "Materials"], label="commodity bid"),
        ScenarioImpact("macro", "bearish", 0.5, 0.78, label="cost-push inflation"),
    ],
))

_register(Scenario(
    name="Volatility Spike",
    description="A sudden VIX surge forces de-leveraging; crowded trades unwind first.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("structural_risk", "bullish", 0.7, 0.85, label="forced de-leveraging"),
        ScenarioImpact("tactical", "bearish", 0.6, 0.82, label="momentum break"),
        ScenarioImpact("sentiment", "bearish", 0.5, 0.78, label="fear spike"),
    ],
))

_register(Scenario(
    name="China Slowdown",
    description="China's growth disappoints, dragging global industrials and materials.",
    regime=RISK_OFF,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.6, 0.82, label="global demand drag"),
        ScenarioImpact("tactical", "bearish", 0.5, 0.78, sectors=["Materials", "Industrials"], label="export weakness"),
    ],
))

_register(Scenario(
    name="Credit Crunch",
    description="Lending dries up; leveraged and lower-quality balance sheets get punished.",
    regime=LIQUIDITY_CONTRACTION,
    impacts=[
        ScenarioImpact("structural_risk", "bullish", 0.7, 0.88, label="refinancing risk"),
        ScenarioImpact("macro", "bearish", 0.6, 0.82, label="credit contraction"),
        ScenarioImpact("structural_risk", "bullish", 0.5, 0.78, sectors=["Financials"], label="loan losses"),
    ],
))

_register(Scenario(
    name="Bond Yield Spike",
    description="Long yields jump on supply fears; the highest-multiple names re-rate down.",
    regime=INFLATIONARY,
    impacts=[
        ScenarioImpact("macro", "bearish", 0.7, 0.85, label="discount-rate shock"),
        ScenarioImpact("structural_risk", "bullish", 0.6, 0.8, sectors=["Fixed Income"], label="duration risk"),
        ScenarioImpact("tactical", "bearish", 0.5, 0.76, sectors=["Technology"], label="growth de-rating"),
    ],
))

_register(Scenario(
    name="Melt-Up Bubble",
    description="Speculative euphoria sends risk vertical — great until the air gets thin.",
    regime=RISK_ON,
    impacts=[
        ScenarioImpact("tactical", "bullish", 0.85, 0.88, label="parabolic momentum"),
        ScenarioImpact("sentiment", "bullish", 0.8, 0.85, label="euphoria"),
        ScenarioImpact("structural_risk", "bullish", 0.3, 0.6, label="froth building"),
    ],
))


def get_scenario(name: str) -> Optional[Scenario]:
    """Look up a scenario by name (case/punctuation-insensitive)."""
    return SCENARIOS.get(_slugify(name))


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())
