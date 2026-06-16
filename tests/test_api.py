"""Tests for the HTTP API. Reuses the engine via FastAPI's TestClient.

The engine binds DB_PATH as a default arg at import time, so the API is pinned to
the real DB_PATH. To stay isolated, this fixture backs up any existing working DB,
runs the test against a fresh one created by the app's lifespan bootstrap, then
restores the original — so the suite never clobbers a developer's db.
"""

import os
import shutil

import pytest
from fastapi.testclient import TestClient

from config.settings import DB_PATH


@pytest.fixture
def client():
    backup = DB_PATH + ".testbak"
    existed = os.path.exists(DB_PATH)
    if existed:
        shutil.move(DB_PATH, backup)
    try:
        from api import app as app_module
        with TestClient(app_module.app) as c:   # lifespan bootstraps a fresh db
            yield c
    finally:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if existed:
            shutil.move(backup, DB_PATH)


def test_health_and_status(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    s = client.get("/api/status").json()
    assert s["model_version"] == "1.0.0"
    assert s["signal_source"] == "manual"
    assert "macro" in s["weights"]


def test_universe_seeded_and_mutations(client):
    assets = client.get("/api/universe").json()["assets"]
    assert len(assets) >= 25

    client.post("/api/universe", params={"ticker": "ZZZ", "name": "Zeta", "sector": "Tech"})
    assert "ZZZ" in [a["ticker"] for a in client.get("/api/universe").json()["assets"]]

    client.delete("/api/universe/ZZZ")
    assert "ZZZ" not in [a["ticker"] for a in client.get("/api/universe").json()["assets"]]


def test_scan_known_and_unknown(client):
    r = client.get("/api/scan/NVDA")           # has a committed signal file
    assert r.status_code == 200
    body = r.json()
    assert body["entity"] == "NVDA"
    assert body["classification"] == "CORE"
    assert set(body["components"]) == {"mas", "tas", "sas", "srs"}

    assert client.get("/api/scan/ZZZZ").status_code == 404


def test_recommend_and_portfolio(client):
    rec = client.get("/api/recommend").json()
    assert rec["recommendations"]
    assert rec["recommendations"][0]["rank"] == 1

    port = client.get("/api/portfolio").json()
    assert abs(port["total_weight"] - 1.0) < 0.01
    assert "core" in port["sleeves"]


def test_scenarios_and_run(client):
    names = [s["name"] for s in client.get("/api/scenarios").json()["scenarios"]]
    assert "Rate Shock +200bps" in names

    report = client.post("/api/scenario/Rate Shock +200bps").json()
    assert report["scenario"] == "Rate Shock +200bps"
    assert report["entities"]
    assert report["portfolio_base_acs"] <= report["portfolio_baseline_acs"]


def test_compare_and_alerts(client):
    cmp = client.get("/api/compare", params={"a": "NVDA", "b": "AMD"}).json()
    assert cmp["a"]["entity"] == "NVDA" and cmp["b"]["entity"] == "AMD"
    assert "acs" in cmp["delta"]

    client.get("/api/brief")                    # fires alerts
    alerts = client.get("/api/alerts").json()["alerts"]
    assert isinstance(alerts, list)
