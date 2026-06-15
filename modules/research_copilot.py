"""
Research Copilot
----------------
Reads a financial document (earnings-call transcript, 10-K excerpt, news
article) and uses Claude Sonnet to extract structured signals: overall
sentiment, forward-guidance change, and accounting red flags. The extraction
is mapped into harmonizer-compatible signals for the ACS pipeline.

Structured extraction uses `client.messages.parse()` with a Pydantic schema, so
the model is constrained to valid output. The Anthropic client is injectable for
offline testing; in production it is built from settings.
"""

from typing import Literal

from pydantic import BaseModel, Field

from modules.base import make_signal, get_client, ANTHROPIC_MODEL


class ResearchExtraction(BaseModel):
    """Schema the model must populate."""
    sentiment_direction: Literal["bullish", "bearish", "neutral"]
    sentiment_magnitude: float = Field(ge=0.0, le=1.0, description="Strength of the sentiment, 0-1")
    sentiment_confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the read, 0-1")
    guidance_change: Literal["raised", "lowered", "maintained", "none"]
    accounting_flags: list[str] = Field(default_factory=list, description="Accounting/quality concerns; empty if none")
    summary: str = Field(description="One-sentence justification")


SYSTEM_PROMPT = (
    "You are a sell-side equity research analyst. Read the provided financial "
    "document and extract a structured, evidence-based assessment. Be conservative: "
    "only raise accounting flags when the text gives concrete cause (restatements, "
    "rising DSO, aggressive revenue recognition, going-concern language, auditor "
    "changes). Judge sentiment from substance, not tone."
)

GUIDANCE_TO_DIRECTION = {
    "raised": "bullish",
    "lowered": "bearish",
    "maintained": "neutral",
    "none": None,
}


class ResearchCopilot:

    def __init__(self, client=None, model: str = ANTHROPIC_MODEL):
        self._client = client
        self.model = model

    def build_messages(self, document_text: str) -> list[dict]:
        return [{
            "role": "user",
            "content": (
                "Extract the structured assessment for the following document.\n\n"
                f"<document>\n{document_text}\n</document>"
            ),
        }]

    def extract(self, document_text: str) -> ResearchExtraction:
        client = get_client(self._client)
        response = client.messages.parse(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.build_messages(document_text),
            output_format=ResearchExtraction,
        )
        return response.parsed_output

    def to_signals(self, entity: str, extraction: ResearchExtraction) -> list[dict]:
        """Map an extraction into harmonizer-compatible signals."""
        signals = [
            make_signal(
                entity, "sentiment", extraction.sentiment_direction,
                extraction.sentiment_magnitude, extraction.sentiment_confidence,
                source="research_copilot:sentiment",
                raw_payload={"summary": extraction.summary},
            )
        ]

        guidance_dir = GUIDANCE_TO_DIRECTION.get(extraction.guidance_change)
        if guidance_dir:
            signals.append(make_signal(
                entity, "sentiment", guidance_dir,
                magnitude=0.7, confidence=0.75,
                source="research_copilot:guidance",
                raw_payload={"guidance_change": extraction.guidance_change},
            ))

        if extraction.accounting_flags:
            # Accounting concerns raise structural risk (bullish == HIGH risk).
            magnitude = min(1.0, 0.4 + 0.2 * len(extraction.accounting_flags))
            signals.append(make_signal(
                entity, "structural_risk", "bullish",
                magnitude=magnitude, confidence=0.7,
                source="research_copilot:accounting",
                raw_payload={"flags": extraction.accounting_flags},
            ))

        return signals

    def analyze(self, entity: str, document_text: str) -> list[dict]:
        """Full path: extract via the model, then map to signals."""
        return self.to_signals(entity, self.extract(document_text))
