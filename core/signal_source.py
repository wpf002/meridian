"""
Signal Source
-------------
Abstracts where an entity's raw signals come from. Every source implements
`for_ticker(ticker) -> (signals, error)`.

  - ManualSignalSource:   reads data/inputs/<TICKER>.json (Phase 1 behavior)
  - AuroraSignalSource:    ingests from AURORA (integrations/aurora)
  - FallbackSignalSource:  tries a primary, falls back to a secondary

default_source() picks AURORA when it's enabled and reachable (with manual as
fallback), otherwise manual-only — so manual input always remains available.
"""

from core.signal_loader import load_signals_for
from config.settings import AURORA_ENABLED


class ManualSignalSource:
    def for_ticker(self, ticker: str):
        return load_signals_for(ticker)


class FallbackSignalSource:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def for_ticker(self, ticker: str):
        signals, error = self.primary.for_ticker(ticker)
        if signals:
            return signals, None
        return self.fallback.for_ticker(ticker)


def default_source(llm_client=None) -> tuple[object, str]:
    """
    Return (source, label). Uses AURORA (with manual fallback) when enabled and
    reachable; otherwise manual-only.
    """
    if AURORA_ENABLED:
        try:
            from integrations.aurora.ingestion import AuroraSignalSource
            aurora = AuroraSignalSource(llm_client=llm_client)
            if aurora.available():
                return FallbackSignalSource(aurora, ManualSignalSource()), "AURORA"
        except Exception:
            pass
    return ManualSignalSource(), "manual"
