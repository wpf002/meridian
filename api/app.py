"""
Meridian HTTP API
-----------------
A thin FastAPI layer over the existing engine. Every endpoint reuses the same
pipeline / universe / constructor / simulator the CLI uses — no scoring logic
lives here, only request handling and JSON shaping.

Run with:  python -m api          (or: uvicorn api.app:app --reload)
Docs at:   http://localhost:8800/docs
"""

import time
import asyncio
import logging
import threading
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

log = logging.getLogger("meridian.api")
if not log.handlers:  # surface warmer/background logs alongside uvicorn's
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
    log.propagate = False


async def _warm_loop(app: FastAPI, interval: int):
    """
    Periodically re-score the universe in the background so the per-ticker
    sentiment cache never goes cold — keeping every page load on the fast warm
    path. Force-refreshes on each pass (resetting TTLs); errors are logged and
    never crash the loop. Cancelled on shutdown.
    """
    from config.settings import UNIVERSE_SCAN_LIMIT

    source = app.state.source
    while True:
        try:
            tickers = AssetUniverse().tickers()
            if UNIVERSE_SCAN_LIMIT:
                tickers = tickers[:UNIVERSE_SCAN_LIMIT]
            refreshed = await asyncio.to_thread(source.warm, tickers)
            # Rebuild the cached scan + scenario baseline while the sentiment
            # cache is hot, so the next page load / scenario run is instant.
            await asyncio.to_thread(_scan_universe, True)
            await asyncio.to_thread(_scenario_baseline, True)
            # Grade any calls whose 90-day window has elapsed, using real prices.
            graded = await asyncio.to_thread(
                PerformanceTracker().resolve_due, _aurora_price_lookup
            )
            if graded:
                log.info("auto-graded %s due call(s)", graded)
            log.info("universe warmer refreshed %s tickers", refreshed)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # keep the loop alive across transient failures
            log.warning("universe warmer pass failed: %s", e)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from config.settings import UNIVERSE_REFRESH_SECONDS

    bootstrap.bootstrap()
    # Enable LLM sentiment scoring when an Anthropic key is configured.
    llm = None
    try:
        llm = get_client()
    except RuntimeError:
        pass
    app.state.source, app.state.source_label = default_source(llm_client=llm)

    # Start the background cache warmer when the live source supports it.
    app.state.warmer = None
    if UNIVERSE_REFRESH_SECONDS > 0 and hasattr(app.state.source, "warm"):
        app.state.warmer = asyncio.create_task(_warm_loop(app, UNIVERSE_REFRESH_SECONDS))

    yield

    warmer = getattr(app.state, "warmer", None)
    if warmer:
        warmer.cancel()
        try:
            await warmer
        except asyncio.CancelledError:
            pass


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


# Cache the assembled universe scan so recommend/portfolio/brief don't each run a
# fresh scan on every page load. Guarded by a lock so concurrent requests share
# one scan instead of stampeding.
_scan_cache = {"at": 0.0, "data": None}
_scan_lock = threading.Lock()


def _scan_universe(force: bool = False):
    from config.settings import UNIVERSE_RESULT_TTL
    with _scan_lock:
        cached = _scan_cache["data"]
        if not force and cached is not None and (time.time() - _scan_cache["at"]) < UNIVERSE_RESULT_TTL:
            return cached
        data = MeridianPipeline().run_universe(AssetUniverse().tickers(), source=_source())
        _scan_cache["at"] = time.time()
        _scan_cache["data"] = data
        # Record today's calls so the track record can grade them later
        # (idempotent — at most one row per ticker per day).
        try:
            scans = data[0]
            PerformanceTracker().snapshot_decisions([
                {"run_id": s.run_id, "ticker": s.entity,
                 "classification": s.classification, "acs": s.result.acs}
                for s in scans
            ])
        except Exception as e:
            log.warning("decision snapshot failed: %s", e)
        return data


def _aurora_price_lookup(ticker: str):
    """(timestamp, close) price history for a ticker via AURORA, or [] if
    unavailable (e.g. the manual source has no price feed)."""
    source = app.state.source
    client = getattr(getattr(source, "primary", source), "client", None)
    if client is None:
        return []
    try:
        return [(p.timestamp, p.close) for p in client.quote_history(ticker, period="6mo")]
    except Exception:
        return []


# Raw per-ticker signals for every universe asset, fetched concurrently and
# cached. Reused across scenario runs so flipping between scenarios is fast
# instead of re-fetching the whole universe serially each time.
_baseline_cache = {"at": 0.0, "data": None}
_baseline_lock = threading.Lock()


def _scenario_baseline(force: bool = False):
    from concurrent.futures import ThreadPoolExecutor
    from config.settings import UNIVERSE_RESULT_TTL, UNIVERSE_SCAN_LIMIT
    with _baseline_lock:
        cached = _baseline_cache["data"]
        if not force and cached is not None and (time.time() - _baseline_cache["at"]) < UNIVERSE_RESULT_TTL:
            return cached
        assets = AssetUniverse().get_all()
        if UNIVERSE_SCAN_LIMIT:
            assets = assets[:UNIVERSE_SCAN_LIMIT]
        source = _source()

        def fetch(asset):
            try:
                signals, error = source.for_ticker(asset["ticker"])
            except Exception:
                return None
            if error or not signals:
                return None
            return {"ticker": asset["ticker"], "sector": asset["sector"],
                    "asset_class": asset["asset_class"], "signals": signals}

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(assets)))) as ex:
            data = [d for d in ex.map(fetch, assets) if d]
        _baseline_cache["at"] = time.time()
        _baseline_cache["data"] = data
        return data


# --- meta ------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "signal_source": getattr(app.state, "source_label", "manual")}


@app.get("/api/status")
def status():
    from config.settings import OUTCOME_PERIOD_DAYS
    registry = ModelRegistry()
    active = registry.get_active()
    tracker = PerformanceTracker()
    return {
        "model_version": active["version"] if active else None,
        "weights": active["weights"] if active else {},
        "thresholds": active["thresholds"] if active else {},
        "signal_source": getattr(app.state, "source_label", "manual"),
        "accuracy": tracker.get_accuracy_by_classification(),
        "pending_outcomes": tracker.count_pending(),
        "outcome_period_days": OUTCOME_PERIOD_DAYS,
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
    data = _scenario_baseline()
    if not data:
        raise HTTPException(status_code=400, detail="No assets with signals")
    return Simulator(pipeline=MeridianPipeline()).run_scenario(scenario, data).to_dict()


# --- reporting -------------------------------------------------------------

@app.get("/api/regime")
def regime():
    scans, _ = _scan_universe()
    if not scans:
        raise HTTPException(status_code=400, detail="No scored assets to infer a regime")
    return {"regime": classify_current_regime([s.result for s in scans])}


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
