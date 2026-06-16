"""
AURORA Adapter
--------------
Converts AURORA data shapes into Meridian harmonizer-compatible raw signals,
reusing the existing intelligence modules where possible.

  regime    -> macro signal            (fills the macro weight Meridian's own
                                         modules cannot produce)
  history   -> tactical signal(s)      (QuantAssistant momentum)
  fragility -> structural_risk signal  (per-symbol fragility 0-100)
  news      -> sentiment signal(s)     (SentimentFeed, requires an LLM client)
"""

from modules.base import make_signal
from modules.quant_assistant import QuantAssistant
from modules.sentiment_feed import SentimentFeed
from integrations.aurora.schema import RegimeSnapshot, QuoteHistoryPoint, NewsItem


# Regime -> (macro direction, base magnitude)
REGIME_DIRECTION = {
    "RISK-ON": ("bullish", 0.8),
    "RISK-OFF": ("bearish", 0.8),
    "INFLATIONARY": ("bearish", 0.6),
    "LIQUIDITY-CONTRACTION": ("bearish", 0.7),
    "NEUTRAL": ("neutral", 0.5),
}


def macro_signal(entity: str, regime: RegimeSnapshot) -> dict:
    direction, magnitude = REGIME_DIRECTION.get(regime.regime, ("neutral", 0.5))
    return make_signal(
        entity, "macro", direction,
        magnitude=magnitude, confidence=max(0.5, regime.confidence),
        source="aurora:regime",
        raw_payload={"regime": regime.regime, "factors": regime.factors[:4]},
    )


def tactical_signals(entity: str, history: list[QuoteHistoryPoint]) -> list[dict]:
    prices = [p.close for p in history]
    volumes = [p.volume for p in history]
    return QuantAssistant().to_signals(entity, prices, volumes)


def structural_signal(entity: str, fragility: float) -> dict:
    """Map AURORA fragility (0-100) to a structural_risk signal (bullish == high risk)."""
    f = max(0.0, min(1.0, fragility / 100.0))
    if f >= 0.5:
        direction, magnitude = "bullish", f          # elevated risk
    else:
        direction, magnitude = "bearish", 0.25        # benign
    return make_signal(
        entity, "structural_risk", direction,
        magnitude=magnitude, confidence=0.7,
        source="aurora:fragility",
        raw_payload={"fragility": round(fragility, 1)},
    )


def sentiment_signals(entity: str, news: list[NewsItem], llm_client) -> list[dict]:
    """Score AURORA news via the Sentiment Feed module (requires an LLM client)."""
    headlines = [n.headline for n in news if n.headline]
    if not headlines:
        return []
    feed = SentimentFeed(client=llm_client)
    return feed.analyze(headlines, entities=[entity.upper()])
