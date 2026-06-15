"""
Meridian — Entry Point
----------------------
Initializes the database, registers the baseline model version,
and launches the conversational interface.

Usage:
  python main.py
  python main.py --brief        (run daily brief and exit)
  python main.py --status       (print system status and exit)
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from rich.console import Console

from config.settings import DB_PATH
from governance.model_registry import ModelRegistry
from interface.chat import run_chat

console = Console()


def init_db():
    """Initialize the database from schema.sql."""
    schema_path = Path("db/schema.sql")
    if not schema_path.exists():
        console.print("[red]ERROR: db/schema.sql not found[/red]")
        sys.exit(1)

    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_path.read_text())

    console.print(f"[green]Database initialized:[/green] {DB_PATH}")


def ensure_baseline_model():
    """Register baseline model version if none exists."""
    registry = ModelRegistry()
    active = registry.get_active()
    if not active:
        registry.register(
            version="1.0.0",
            notes="Baseline model — initial deployment",
        )
        console.print("[green]Baseline model registered:[/green] v1.0.0")
    else:
        console.print(f"[cyan]Active model:[/cyan] v{active['version']}")


class MeridianCore:
    """
    Stub command dispatcher. Phase 1 scaffold.
    Each cmd_* method will be wired to the full pipeline in subsequent phases.
    """

    def cmd_scan(self, ticker: str):
        console.print(f"[cyan]SCAN[/cyan] {ticker} — Pipeline not yet wired. Phase 1 in progress.")

    def cmd_recommend(self):
        console.print("[cyan]RECOMMEND[/cyan] — Pipeline not yet wired. Phase 2 in progress.")

    def cmd_build_portfolio(self):
        console.print("[cyan]BUILD PORTFOLIO[/cyan] — Pipeline not yet wired. Phase 2 in progress.")

    def cmd_compare(self, ticker_a: str, ticker_b: str):
        console.print(f"[cyan]COMPARE[/cyan] {ticker_a} vs {ticker_b} — Pipeline not yet wired.")

    def cmd_brief(self):
        console.print("[cyan]BRIEF[/cyan] — Pipeline not yet wired. Phase 3 in progress.")

    def cmd_alerts(self):
        console.print("[cyan]ALERTS[/cyan] — Pipeline not yet wired.")

    def cmd_status(self):
        registry = ModelRegistry()
        active = registry.get_active()
        version = active["version"] if active else "none"
        weights = active["weights"] if active else {}
        console.print(f"[bold]MERIDIAN STATUS[/bold]")
        console.print(f"  Model Version : {version}")
        console.print(f"  DB Path       : {DB_PATH}")
        console.print(f"  Weights       : {weights}")


def main():
    parser = argparse.ArgumentParser(description="Meridian Financial Intelligence System")
    parser.add_argument("--brief", action="store_true", help="Run daily brief and exit")
    parser.add_argument("--status", action="store_true", help="Print system status and exit")
    args = parser.parse_args()

    console.print("[bold cyan]MERIDIAN[/bold cyan] — Initializing...")
    init_db()
    ensure_baseline_model()

    core = MeridianCore()

    if args.status:
        core.cmd_status()
        return

    if args.brief:
        core.cmd_brief()
        return

    run_chat(core)


if __name__ == "__main__":
    main()
