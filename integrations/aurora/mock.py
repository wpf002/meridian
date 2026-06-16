"""
Mock AURORA Client
------------------
A drop-in AuroraClient that serves canned responses by overriding the transport
(`_get_json`). Used by tests and for offline demos when the real AURORA terminal
isn't running. The full parse/adapter/ingestion path runs against this exactly as
it would against the live API.
"""

from integrations.aurora.client import AuroraClient


def _uptrend(n: int = 12, start: float = 100.0, step: float = 2.0) -> list[dict]:
    bars = []
    price = start
    for i in range(n):
        bars.append({
            "timestamp": f"2026-06-{i+1:02d}T00:00:00Z",
            "open": price, "high": price + 1, "low": price - 1,
            "close": price + step, "volume": 1_000_000 + i * 50_000,
        })
        price += step
    return bars


class MockAuroraClient(AuroraClient):
    """Serves canned data. `regime_label`/`fragility`/`reachable` are tunable."""

    def __init__(self, regime_label: str = "RISK_ON", confidence: float = 0.8,
                 fragility: float = 30.0, reachable: bool = True):
        super().__init__(base_url="mock://aurora")
        self.regime_label = regime_label
        self.confidence = confidence
        self.fragility_value = fragility
        self.reachable = reachable

    def _get_json(self, path: str, params: dict = None):
        if not self.reachable:
            raise ConnectionError("AURORA unreachable (mock)")

        if path == "/intelligence/regime":
            return {
                "regime": self.regime_label,
                "confidence": self.confidence,
                "factors": ["VIX 15.5 (LOW)", "10Y-2Y +0.25% (POSITIVE)"],
            }
        if path == "/intelligence/fragility":
            sym = (params or {}).get("symbol", "AAPL")
            return {"portfolio_fragility": self.fragility_value,
                    "positions": [{"symbol": sym, "fragility": self.fragility_value}]}
        if path.endswith("/history"):
            return _uptrend()
        if path == "/news":
            syms = (params or {}).get("symbols", "AAPL").split(",")
            return [{
                "id": "n1", "headline": f"{syms[0]} beats estimates on strong demand",
                "source": "Mock", "summary": "Upbeat quarter.", "symbols": syms,
                "published_at": "2026-06-15T12:00:00Z",
            }]
        if path.startswith("/filings/"):
            return [{
                "accession_number": "0000-00", "cik": "0000320193",
                "company": "Mock Co", "form_type": "10-Q",
                "filed_at": "2026-05-01T00:00:00Z", "url": "https://sec.gov/x",
            }]
        return {}

    # Fragility endpoint in the real API is portfolio-wide; for the mock we let
    # callers pass a symbol so the per-symbol lookup resolves.
    def fragility_for(self, symbol: str) -> float:
        data = self._get_json("/intelligence/fragility", {"symbol": symbol})
        return float(data["positions"][0]["fragility"])
