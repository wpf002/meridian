"""
Market Sentiment Feed
---------------------
Accepts a batch of headlines / news text and uses Claude Sonnet to score
sentiment per entity, flagging narrative trend shifts. Emits `sentiment`
signals for the ACS pipeline.

Like the Research Copilot, extraction is constrained via `messages.parse()` with
a Pydantic schema, and the Anthropic client is injectable for offline testing.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from modules.base import make_signal, get_client, ANTHROPIC_MODEL
from config.settings import SENTIMENT_MODEL


class EntitySentiment(BaseModel):
    entity: str = Field(description="Ticker or entity the sentiment applies to")
    direction: Literal["bullish", "bearish", "neutral"]
    magnitude: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    narrative_shift: bool = Field(description="True if the prevailing narrative is changing")
    rationale: str = Field(description="One-sentence justification")


class SentimentBatch(BaseModel):
    entities: list[EntitySentiment]


SYSTEM_PROMPT = (
    "You are a market sentiment analyst. Given recent headlines, score the "
    "sentiment for each named entity (or sector). Distinguish durable narrative "
    "shifts from noise: set narrative_shift=true only when the headlines suggest "
    "the dominant story is reversing, not merely a one-off data point."
)


class SentimentFeed:

    def __init__(self, client=None, model: str = SENTIMENT_MODEL):
        self._client = client
        self.model = model

    def build_messages(self, headlines: list[str], entities: Optional[list[str]] = None) -> list[dict]:
        focus = (
            f"Score sentiment for these entities: {', '.join(entities)}.\n\n"
            if entities else
            "Identify the entities/sectors mentioned and score each.\n\n"
        )
        joined = "\n".join(f"- {h}" for h in headlines)
        return [{"role": "user", "content": f"{focus}<headlines>\n{joined}\n</headlines>"}]

    def score(self, headlines: list[str], entities: Optional[list[str]] = None) -> SentimentBatch:
        client = get_client(self._client)
        response = client.messages.parse(
            model=self.model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=self.build_messages(headlines, entities),
            output_format=SentimentBatch,
        )
        return response.parsed_output

    def to_signals(self, batch: SentimentBatch) -> list[dict]:
        """Map per-entity sentiment into harmonizer-compatible signals."""
        signals = []
        for e in batch.entities:
            # A narrative shift sharpens conviction in the move.
            magnitude = min(1.0, e.magnitude + (0.15 if e.narrative_shift else 0.0))
            signals.append(make_signal(
                e.entity, "sentiment", e.direction,
                magnitude=magnitude, confidence=e.confidence,
                source="sentiment_feed:news",
                raw_payload={"narrative_shift": e.narrative_shift, "rationale": e.rationale},
            ))
        return signals

    def analyze(self, headlines: list[str], entities: Optional[list[str]] = None) -> list[dict]:
        """Full path: score via the model, then map to signals."""
        return self.to_signals(self.score(headlines, entities))
