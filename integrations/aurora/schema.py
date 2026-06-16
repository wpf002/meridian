"""
AURORA ⇄ Meridian Shared Signal Schema Contract
-----------------------------------------------
Mirrors the data shapes AURORA (the bloomberg terminal) exposes over its HTTP
API, and documents how each maps onto a Meridian harmonized signal.

AURORA source of truth (backend/models/schemas.py): Quote, QuoteHistoryPoint,
MacroSeries, NewsItem, FilingEntry, and the /intelligence/regime response.

Signal mapping (AURORA -> Meridian signal_type):
  /intelligence/regime         -> macro            (regime direction & confidence)
  /quotes/{sym}/history        -> tactical         (momentum via QuantAssistant)
  /intelligence/fragility      -> structural_risk  (per-symbol fragility 0-100)
  /news?symbols=               -> sentiment        (LLM scoring, optional)
  /filings/{sym}               -> structural_risk  (forensic context, optional)
"""

from dataclasses import dataclass, field
from typing import Optional


# AURORA regime labels use underscores; Meridian uses hyphens. AURORA also has
# STAGFLATIONARY / NEUTRAL which Meridian treats as risk-off / neutral.
_REGIME_NORMALIZE = {
    "RISK_ON": "RISK-ON",
    "RISK_OFF": "RISK-OFF",
    "INFLATIONARY": "INFLATIONARY",
    "LIQUIDITY_CONTRACTION": "LIQUIDITY-CONTRACTION",
    "STAGFLATIONARY": "LIQUIDITY-CONTRACTION",
    "NEUTRAL": "NEUTRAL",
}


def normalize_regime(label: str) -> str:
    if not label:
        return "NEUTRAL"
    key = label.strip().upper().replace("-", "_")
    return _REGIME_NORMALIZE.get(key, label.strip().upper().replace("_", "-"))


@dataclass
class QuoteHistoryPoint:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    @classmethod
    def from_dict(cls, d: dict) -> "QuoteHistoryPoint":
        return cls(
            timestamp=str(d.get("timestamp", "")),
            open=float(d.get("open", 0) or 0),
            high=float(d.get("high", 0) or 0),
            low=float(d.get("low", 0) or 0),
            close=float(d.get("close", 0) or 0),
            volume=int(d.get("volume", 0) or 0),
        )


@dataclass
class NewsItem:
    id: str
    headline: str
    source: str
    summary: Optional[str] = None
    symbols: list = field(default_factory=list)
    published_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "NewsItem":
        return cls(
            id=str(d.get("id", "")),
            headline=d.get("headline", ""),
            source=d.get("source", ""),
            summary=d.get("summary"),
            symbols=d.get("symbols", []) or [],
            published_at=str(d.get("published_at", "")),
        )


@dataclass
class FilingEntry:
    accession_number: str
    cik: str
    company: str
    form_type: str
    filed_at: str
    url: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "FilingEntry":
        return cls(
            accession_number=str(d.get("accession_number", "")),
            cik=str(d.get("cik", "")),
            company=d.get("company", ""),
            form_type=d.get("form_type", ""),
            filed_at=str(d.get("filed_at", "")),
            url=d.get("url", ""),
        )


@dataclass
class RegimeSnapshot:
    regime: str                       # normalized to Meridian labels
    confidence: float = 0.5
    factors: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "RegimeSnapshot":
        return cls(
            regime=normalize_regime(d.get("regime", "NEUTRAL")),
            confidence=float(d.get("confidence", 0.5) or 0.5),
            factors=d.get("factors", []) or [],
        )
