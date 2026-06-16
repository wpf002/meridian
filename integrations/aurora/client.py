"""
AURORA HTTP Client
------------------
Thin client over AURORA's REST API. Uses the standard library (urllib) so it
adds no dependency. All network access goes through `_get_json`, which the mock
client overrides — so the parsing/adapter layers are exercised in tests without
touching the network.
"""

import json
import urllib.parse
import urllib.request

from config.settings import AURORA_BASE_URL
from integrations.aurora.schema import (
    QuoteHistoryPoint, NewsItem, FilingEntry, RegimeSnapshot,
)


class AuroraClient:

    def __init__(self, base_url: str = AURORA_BASE_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get_json(self, path: str, params: dict = None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_list(self, path: str, params: dict = None) -> list:
        """List-returning endpoints: treat 'no data' (404/empty) as [] rather than an error."""
        try:
            data = self._get_json(path, params)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def health(self) -> bool:
        """True if AURORA's API answers the regime endpoint."""
        try:
            self._get_json("/intelligence/regime")
            return True
        except Exception:
            return False

    def regime(self) -> RegimeSnapshot:
        return RegimeSnapshot.from_dict(self._get_json("/intelligence/regime"))

    def quote_history(self, symbol: str, period: str = "3mo", interval: str = "1d") -> list[QuoteHistoryPoint]:
        data = self._get_list(f"/quotes/{symbol}/history", {"period": period, "interval": interval})
        return [QuoteHistoryPoint.from_dict(d) for d in data]

    def fragility(self) -> dict[str, float]:
        """Return {symbol: fragility 0-100} from the intelligence fragility snapshot."""
        data = self._get_json("/intelligence/fragility")
        out = {}
        for pos in (data.get("positions", []) if isinstance(data, dict) else []):
            sym = pos.get("symbol")
            if sym is not None:
                out[sym.upper()] = float(pos.get("fragility", 0) or 0)
        return out

    def news(self, symbols: list[str], limit: int = 20) -> list[NewsItem]:
        data = self._get_list("/news", {"symbols": ",".join(symbols), "limit": limit})
        return [NewsItem.from_dict(d) for d in data]

    def filings(self, symbol: str, forms: str = "10-K,10-Q,8-K", limit: int = 10) -> list[FilingEntry]:
        data = self._get_list(f"/filings/{symbol}", {"forms": forms, "limit": limit})
        return [FilingEntry.from_dict(d) for d in data]
