"""
Syntrackr Overlay
-----------------
Surfaces Syntrackr's tax-loss-harvesting output as an overlay on Meridian's
recommendations. Syntrackr exposes harvest candidates via /api/harvest; its tax
engine reports wash-sale risk (is_wash_sale / safe_to_harvest).

This module defines the contract and a mock source. A live HTTP client would
mirror integrations/aurora/client.py against SYNTRACKR_BASE_URL; until Syntrackr
is wired, the overlay is empty unless SYNTRACKR_ENABLED and a source is provided.
"""

from dataclasses import dataclass


@dataclass
class TLHCandidate:
    ticker: str
    unrealized_loss: float        # negative dollar amount
    safe_to_harvest: bool         # passes the wash-sale check
    wash_sale: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "TLHCandidate":
        return cls(
            ticker=str(d.get("ticker", "")).upper(),
            unrealized_loss=float(d.get("unrealized_loss", 0) or 0),
            safe_to_harvest=bool(d.get("safe_to_harvest", False)),
            wash_sale=bool(d.get("is_wash_sale", d.get("wash_sale", False))),
        )


class MockSyntrackrSource:
    """Serves canned harvest candidates for tests/offline demos."""

    def __init__(self, candidates: list[dict] = None):
        self._candidates = candidates or [
            {"ticker": "TLT", "unrealized_loss": -1850.0, "safe_to_harvest": True, "is_wash_sale": False},
            {"ticker": "XOM", "unrealized_loss": -620.0, "safe_to_harvest": False, "is_wash_sale": True},
        ]

    def candidates(self) -> list[TLHCandidate]:
        return [TLHCandidate.from_dict(c) for c in self._candidates]


def build_overlay(tickers: list[str], source) -> dict[str, TLHCandidate]:
    """Return {ticker: TLHCandidate} for harvest candidates that are in the universe."""
    universe = {t.upper() for t in tickers}
    return {c.ticker: c for c in source.candidates() if c.ticker in universe}
