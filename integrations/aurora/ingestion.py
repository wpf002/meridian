"""
AURORA Ingestion
----------------
Assembles a full raw-signal set for a ticker from AURORA, replacing manual
signal entry. Each source is fetched independently and failures are isolated —
a missing news feed never blocks the macro/tactical signals.

Implements the signal-source protocol (`for_ticker(ticker) -> (signals, error)`)
so it slots into the pipeline alongside the manual loader.
"""

from integrations.aurora.client import AuroraClient
from integrations.aurora import adapter


class AuroraSignalSource:

    def __init__(self, client: AuroraClient = None, llm_client=None):
        self.client = client or AuroraClient()
        self.llm_client = llm_client      # optional — enables sentiment scoring
        self._regime = None               # memoized for the source's lifetime
        self._fragility = None

    def available(self) -> bool:
        return self.client.health()

    def _get_regime(self):
        if self._regime is None:
            self._regime = self.client.regime()
        return self._regime

    def _get_fragility(self) -> dict:
        if self._fragility is None:
            try:
                self._fragility = self.client.fragility()
            except Exception:
                self._fragility = {}
        return self._fragility

    def for_ticker(self, ticker: str):
        """Return (raw_signals, error). error is set only when nothing could be fetched."""
        ticker = ticker.upper()
        signals: list[dict] = []
        errors: list[str] = []

        # Macro from regime (the signal Meridian's own modules can't produce).
        try:
            signals.append(adapter.macro_signal(ticker, self._get_regime()))
        except Exception as e:
            errors.append(f"regime: {e}")

        # Tactical from market-data history.
        try:
            history = self.client.quote_history(ticker)
            signals.extend(adapter.tactical_signals(ticker, history))
        except Exception as e:
            errors.append(f"history: {e}")

        # Structural risk from fragility (if this ticker is covered).
        try:
            frag = self._get_fragility().get(ticker)
            if frag is not None:
                signals.append(adapter.structural_signal(ticker, frag))
        except Exception as e:
            errors.append(f"fragility: {e}")

        # Sentiment from news — only when an LLM client is configured.
        if self.llm_client:
            try:
                news = self.client.news([ticker])
                signals.extend(adapter.sentiment_signals(ticker, news, self.llm_client))
            except Exception as e:
                errors.append(f"news: {e}")

        if not signals:
            return None, f"AURORA returned no signals for {ticker}" + (f" ({'; '.join(errors)})" if errors else "")
        return signals, None
