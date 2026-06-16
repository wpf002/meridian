"""
Bootstrap
---------
Silent, side-effect-only startup steps shared by the CLI and the API: create the
database from schema, register the baseline model, and seed the asset universe.
Callers (CLI) print their own status; the API runs these on startup.
"""

import sqlite3
from pathlib import Path

from config.settings import DB_PATH
from governance.model_registry import ModelRegistry
from classification.asset_universe import AssetUniverse
from classification.seed_universe import seed_universe


def init_db() -> None:
    """Create the database from db/schema.sql (idempotent)."""
    schema_path = Path("db/schema.sql")
    if not schema_path.exists():
        raise FileNotFoundError("db/schema.sql not found")
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_path.read_text())


def ensure_baseline_model() -> tuple[str, bool]:
    """Register baseline model if none active. Returns (version, newly_registered)."""
    registry = ModelRegistry()
    active = registry.get_active()
    if not active:
        registry.register(version="1.0.0", notes="Baseline model — initial deployment")
        return "1.0.0", True
    return active["version"], False


def ensure_universe_seeded() -> int:
    """Seed the universe if empty. Returns the number of assets added (0 if already seeded)."""
    return seed_universe()


def bootstrap() -> dict:
    """Run all startup steps. Returns a small status summary."""
    init_db()
    version, registered = ensure_baseline_model()
    added = ensure_universe_seeded()
    return {
        "model_version": version,
        "model_registered": registered,
        "assets_seeded": added,
        "universe_size": len(AssetUniverse().tickers()),
    }
