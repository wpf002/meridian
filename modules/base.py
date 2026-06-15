"""
Module Base
-----------
Shared helpers for the intelligence modules.

Every module produces signals in the harmonizer-compatible schema
(entity, signal_type, direction, magnitude, confidence, source, raw_payload)
so its output can be fed straight into SignalHarmonizer / MeridianPipeline.

LLM-backed modules accept an injectable Anthropic client so they can be unit
tested offline; in production the client is constructed lazily from settings.
"""

from typing import Optional

from config.settings import ANTHROPIC_API_KEY, ANTHROPIC_MODEL


def make_signal(
    entity: str,
    signal_type: str,
    direction: str,
    magnitude: float,
    confidence: float,
    source: str,
    raw_payload: Optional[dict] = None,
) -> dict:
    """Build a harmonizer-compatible raw signal dict with clamped numeric fields."""
    return {
        "entity": entity.upper(),
        "signal_type": signal_type,
        "direction": direction,
        "magnitude": round(_clamp(magnitude), 4),
        "confidence": round(_clamp(confidence), 4),
        "source": source,
        "raw_payload": raw_payload or {},
    }


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def get_client(client=None):
    """
    Return an Anthropic client. If one is injected, use it (tests pass a fake).
    Otherwise construct from settings; raises if no API key is configured.
    """
    if client is not None:
        return client
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — set it in .env to use the LLM modules, "
            "or supply signals manually."
        )
    import anthropic

    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


__all__ = ["make_signal", "get_client", "ANTHROPIC_MODEL"]
