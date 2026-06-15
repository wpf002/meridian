"""
Quant Assistant
---------------
Deterministic technical analysis. Accepts a price series (and optional volume)
and computes momentum, volatility, and basic technical structure, emitting a
`tactical` signal for the ACS pipeline. No LLM — fully reproducible and testable.

Also provides a lightweight backtesting scaffold: replay historical signal sets
through the scoring engine to see what the ACS would have been.
"""

from dataclasses import dataclass, field
from statistics import mean, pstdev

from modules.base import make_signal
from core.signal_harmonizer import SignalHarmonizer
from core.scoring_engine import ScoringEngine, ACSResult


@dataclass
class QuantMetrics:
    entity: str
    n: int
    cumulative_return: float = 0.0   # total return over the series
    momentum: float = 0.0            # average per-step return
    volatility: float = 0.0          # stdev of per-step returns
    price_vs_sma: float = 0.0        # last price vs simple moving average
    trend: str = "flat"             # up | down | flat
    notes: list = field(default_factory=list)


class QuantAssistant:

    # Cumulative return beyond this (in either direction) is directional, not noise.
    DIRECTION_THRESHOLD = 0.02

    def compute(self, entity: str, prices: list[float]) -> QuantMetrics:
        """Compute technical metrics from a price series (oldest -> newest)."""
        m = QuantMetrics(entity=entity.upper(), n=len(prices))
        if len(prices) < 2:
            m.notes.append("Insufficient price history (need >= 2 points)")
            return m

        returns = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
        m.cumulative_return = prices[-1] / prices[0] - 1
        m.momentum = mean(returns)
        m.volatility = pstdev(returns) if len(returns) > 1 else 0.0
        sma = mean(prices)
        m.price_vs_sma = prices[-1] / sma - 1 if sma else 0.0

        if m.cumulative_return > self.DIRECTION_THRESHOLD:
            m.trend = "up"
        elif m.cumulative_return < -self.DIRECTION_THRESHOLD:
            m.trend = "down"
        else:
            m.trend = "flat"
        return m

    def to_signals(self, entity: str, prices: list[float], volumes: list[float] = None) -> list[dict]:
        """Produce a `tactical` signal from the price (and optional volume) series."""
        m = self.compute(entity, prices)
        if m.n < 2:
            return []

        direction = {"up": "bullish", "down": "bearish", "flat": "neutral"}[m.trend]

        # Magnitude scales with the size of the move (a ~20% move ~ full magnitude).
        magnitude = min(1.0, abs(m.cumulative_return) * 5)
        if m.trend == "flat":
            magnitude = max(magnitude, 0.2)

        # Confidence rises with sample size, falls with volatility, and lifts a
        # little when volume confirms the move (rising average volume).
        sample_conf = min(1.0, m.n / 20)
        vol_penalty = min(0.5, m.volatility * 5)
        confidence = max(0.3, sample_conf - vol_penalty)
        if volumes and len(volumes) >= 2 and mean(volumes[len(volumes) // 2:]) > mean(volumes[: len(volumes) // 2]):
            confidence = min(1.0, confidence + 0.1)

        return [
            make_signal(
                entity, "tactical", direction, magnitude, confidence,
                source="quant_assistant:momentum",
                raw_payload={
                    "cumulative_return": round(m.cumulative_return, 4),
                    "momentum": round(m.momentum, 5),
                    "volatility": round(m.volatility, 5),
                    "price_vs_sma": round(m.price_vs_sma, 4),
                    "trend": m.trend,
                    "points": m.n,
                },
            )
        ]

    def backtest(self, entity: str, historical_signal_sets: list[list[dict]]) -> list[ACSResult]:
        """
        Scaffold: replay a chronological list of raw signal sets through the
        harmonizer + scoring engine and return the ACS each set would have
        produced. Each element is one point in time (a list of raw signal dicts).
        """
        harmonizer = SignalHarmonizer()
        engine = ScoringEngine()
        ticker = entity.upper()
        results: list[ACSResult] = []
        for raws in historical_signal_sets:
            # Default the entity onto each raw signal so callers need not repeat it.
            stamped = [{"entity": ticker, **r} for r in raws]
            signals = harmonizer.harmonize_batch(stamped)
            results.append(engine.score(ticker, signals))
        return results
