"""
AURORA Ingestion
----------------
Assembles a full raw-signal set for a ticker from AURORA, replacing manual
signal entry. Each source is fetched independently and failures are isolated —
a missing news feed never blocks the macro/tactical signals.

Implements the signal-source protocol (`for_ticker(ticker) -> (signals, error)`)
so it slots into the pipeline alongside the manual loader.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

from config.settings import SENTIMENT_CACHE_TTL
from integrations.aurora.client import AuroraClient
from integrations.aurora import adapter


class AuroraSignalSource:

    def __init__(self, client: AuroraClient = None, llm_client=None, sentiment_ttl: int = SENTIMENT_CACHE_TTL):
        self.client = client or AuroraClient()
        self.llm_client = llm_client      # optional — enables sentiment scoring
        self.sentiment_ttl = sentiment_ttl
        self._regime = None               # memoized for the source's lifetime
        self._fragility = None
        self._sentiment_cache = {}        # ticker -> (expires_at, signals)
        self._lock = threading.Lock()     # guards the shared memo under parallel scans
        self._warm_lock = threading.Lock()  # ensures only one warm pass runs at a time

    def _sentiment_for(self, ticker: str, force: bool = False) -> list[dict]:
        """LLM-scored sentiment for a ticker, cached for sentiment_ttl seconds.
        force=True recomputes and resets the TTL even on a cache hit — used by the
        background warmer to keep the cache fresh before it expires."""
        now = time.time()
        if not force:
            hit = self._sentiment_cache.get(ticker)
            if hit and hit[0] > now:
                return hit[1]
        news = self.client.news([ticker])
        signals = adapter.sentiment_signals(ticker, news, self.llm_client)
        self._sentiment_cache[ticker] = (now + self.sentiment_ttl, signals)
        return signals

    def available(self) -> bool:
        return self.client.health()

    def _get_regime(self, force: bool = False):
        with self._lock:
            if self._regime is None or force:
                self._regime = self.client.regime()
            return self._regime

    def _get_fragility(self, force: bool = False) -> dict:
        with self._lock:
            if self._fragility is None or force:
                try:
                    self._fragility = self.client.fragility()
                except Exception:
                    self._fragility = {}
            return self._fragility

    def warm(self, tickers: list[str], max_workers: int = 8) -> int:
        """
        Proactively refresh the regime, fragility and per-ticker sentiment caches
        so a subsequent universe scan hits the fast warm path. Force-recomputes
        even unexpired entries (resetting their TTL), so calling this on an
        interval shorter than sentiment_ttl keeps the cache perpetually warm.

        Returns the number of tickers whose sentiment was refreshed. A second
        concurrent call is a no-op (returns 0) — only one warm pass runs at once.
        """
        if not self.llm_client or not tickers:
            return 0
        if not self._warm_lock.acquire(blocking=False):
            return 0
        try:
            # Refresh the shared macro/structural inputs once up front.
            try:
                self._get_regime(force=True)
                self._get_fragility(force=True)
            except Exception:
                pass

            tickers = [t.upper() for t in tickers]

            def refresh(ticker):
                try:
                    self._sentiment_for(ticker, force=True)
                    return True
                except Exception:
                    return False

            with ThreadPoolExecutor(max_workers=min(max_workers, len(tickers))) as ex:
                return sum(ex.map(refresh, tickers))
        finally:
            self._warm_lock.release()

    def for_ticker(self, ticker: str, lite: bool = False):
        """
        Return (raw_signals, error). error is set only when nothing could be fetched.
        lite=True skips the LLM sentiment call — used for the universe-wide screen so
        ranking a large watchlist stays fast and free. The asset detail uses the full
        path (lite=False), adding news sentiment.
        """
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

        # Sentiment from news — LLM-scored, cached. Skipped in lite mode (the
        # universe screen) so ranking a big watchlist costs nothing.
        if self.llm_client and not lite:
            try:
                signals.extend(self._sentiment_for(ticker))
            except Exception as e:
                errors.append(f"news: {e}")

        if not signals:
            return None, f"AURORA returned no signals for {ticker}" + (f" ({'; '.join(errors)})" if errors else "")
        return signals, None
