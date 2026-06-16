"""
Meridian HTTP API
-----------------
A thin FastAPI layer over the existing engine. Every endpoint reuses the same
pipeline / universe / constructor / simulator the CLI uses — no scoring logic
lives here, only request handling and JSON shaping.

Run with:  python -m api          (or: uvicorn api.app:app --reload)
Docs at:   http://localhost:8800/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from core import bootstrap
from modules.base import get_client
from core.pipeline import MeridianPipeline
from core.signal_source import default_source
from classification.asset_universe import AssetUniverse
from portfolio.constructor import PortfolioConstructor
from meta_learning.performance_tracker import PerformanceTracker
from governance.model_registry import ModelRegistry
from sandbox.scenario_builder import get_scenario, list_scenarios
from sandbox.simulator import Simulator, classify_current_regime
from outputs.alert_system import AlertSystem
from outputs import daily_brief
from api import serializers


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap.bootstrap()
    # Enable LLM sentiment scoring when an Anthropic key is configured.
    llm = None
    try:
        llm = get_client()
    except RuntimeError:
        pass
    app.state.source, app.state.source_label = default_source(llm_client=llm)
    yield


app = FastAPI(title="Meridian API", version="1.0.0", lifespan=lifespan)

# Allow the Vite dev server (and a built frontend) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _source():
    return app.state.source


def _scan_universe():
    tickers = AssetUniverse().tickers()
    return MeridianPipeline().run_universe(tickers, source=_source())


# --- meta ------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "signal_source": getattr(app.state, "source_label", "manual")}


@app.get("/api/status")
def status():
    registry = ModelRegistry()
    active = registry.get_active()
    return {
        "model_version": active["version"] if active else None,
        "weights": active["weights"] if active else {},
        "thresholds": active["thresholds"] if active else {},
        "signal_source": getattr(app.state, "source_label", "manual"),
        "accuracy": PerformanceTracker().get_accuracy_by_classification(),
        "model_history": [
            {"version": m["version"], "notes": m.get("notes")} for m in registry.history()
        ],
    }


# --- universe --------------------------------------------------------------

@app.get("/api/universe")
def universe():
    return {"assets": AssetUniverse().get_all()}


@app.post("/api/universe")
def add_asset(ticker: str, name: str = None, sector: str = None, asset_class: str = None):
    t = ticker.upper()
    AssetUniverse().add(t, name or t, sector=sector, asset_class=asset_class)
    return {"added": t}


@app.delete("/api/universe/{ticker}")
def remove_asset(ticker: str):
    AssetUniverse().remove(ticker.upper())
    return {"removed": ticker.upper()}


# --- scoring ---------------------------------------------------------------

@app.get("/api/scan/{ticker}")
def scan(ticker: str):
    signals, error = _source().for_ticker(ticker)
    if error:
        raise HTTPException(status_code=404, detail=error)
    scan = MeridianPipeline().run_entity(ticker, signals)
    return serializers.scan_to_dict(scan)


@app.get("/api/recommend")
def recommend():
    scans, skipped = _scan_universe()
    return {
        "recommendations": [serializers.recommend_row(s, i) for i, s in enumerate(scans, 1)],
        "skipped": [{"ticker": t, "reason": r} for t, r in skipped],
    }


@app.get("/api/portfolio")
def portfolio():
    scans, skipped = _scan_universe()
    if not scans:
        raise HTTPException(status_code=400, detail="No scored assets to build a portfolio")
    universe = AssetUniverse()
    sector_map = {a["ticker"]: a["sector"] for a in universe.get_all()}
    p = PortfolioConstructor().construct(
        [s.result for s in scans], [s.decision for s in scans], sector_map=sector_map,
    )
    return serializers.portfolio_to_dict(p)


@app.get("/api/compare")
def compare(a: str = Query(...), b: str = Query(...)):
    sa, ea = _source().for_ticker(a)
    sb, eb = _source().for_ticker(b)
    if ea:
        raise HTTPException(status_code=404, detail=ea)
    if eb:
        raise HTTPException(status_code=404, detail=eb)
    pipeline = MeridianPipeline()
    return serializers.compare_to_dict(
        pipeline.run_entity(a, sa), pipeline.run_entity(b, sb),
    )


# --- scenarios -------------------------------------------------------------

@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": [
        {"name": s.name, "slug": s.slug, "description": s.description, "regime": s.regime}
        for s in list_scenarios()
    ]}


@app.post("/api/scenario/{name}")
def run_scenario(name: str):
    scenario = get_scenario(name)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")
    universe = AssetUniverse()
    data = []
    for asset in universe.get_all():
        signals, error = _source().for_ticker(asset["ticker"])
        if error:
            continue
        data.append({"ticker": asset["ticker"], "sector": asset["sector"],
                     "asset_class": asset["asset_class"], "signals": signals})
    if not data:
        raise HTTPException(status_code=400, detail="No assets with signals")
    return Simulator(pipeline=MeridianPipeline()).run_scenario(scenario, data).to_dict()


# --- reporting -------------------------------------------------------------

@app.get("/api/brief")
def brief():
    scans, _ = _scan_universe()
    if not scans:
        raise HTTPException(status_code=400, detail="No scored assets for a brief")
    regime = classify_current_regime([s.result for s in scans])
    alerts = AlertSystem()
    fired = sum(alerts.check_and_fire(s.result, s.prioritized) for s in scans)
    text = daily_brief.generate(
        [s.result for s in scans], [s.prioritized for s in scans],
        [s.decision for s in scans], regime=regime,
    )
    return {"regime": regime, "alerts_fired": fired, "brief": text}


@app.get("/api/alerts")
def alerts():
    return {"alerts": AlertSystem().get_active()}


@app.post("/api/alerts/{alert_id}/ack")
def ack_alert(alert_id: str):
    AlertSystem().acknowledge(alert_id)
    return {"acknowledged": alert_id}
