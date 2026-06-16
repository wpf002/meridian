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
import shlex
import argparse
from pathlib import Path
from datetime import datetime, timezone

from interface.console import console
from config.settings import DB_PATH, DATA_INPUT_PATH, LOG_PATH, SYNTRACKR_ENABLED
from governance.model_registry import ModelRegistry
from core.pipeline import MeridianPipeline
from core.signal_loader import signal_file_path
from core.signal_source import default_source
from classification.asset_universe import AssetUniverse
from classification.seed_universe import seed_universe
from portfolio.constructor import PortfolioConstructor
from meta_learning.performance_tracker import PerformanceTracker
from meta_learning.weight_adjuster import WeightAdjuster
from sandbox.scenario_builder import get_scenario, list_scenarios
from sandbox.simulator import Simulator, classify_current_regime
from outputs.alert_system import AlertSystem
from outputs import daily_brief, weekly_summary
from modules.base import get_client
from interface import nl_fallback
from interface.chat import run_chat
from interface.render import (
    render_scan, render_recommend, render_portfolio, render_compare, render_scenario,
    render_alerts, render_status,
)


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


def ensure_universe_seeded():
    """Seed the asset universe on first boot if it is empty."""
    added = seed_universe()
    if added:
        console.print(f"[green]Asset universe seeded:[/green] {added} assets")
    else:
        count = len(AssetUniverse().tickers())
        console.print(f"[cyan]Active universe:[/cyan] {count} assets")


class MeridianCore:
    """
    Command dispatcher. cmd_scan is wired to the full pipeline (Phase 1).
    Remaining cmd_* methods are wired in subsequent phases.
    """

    def __init__(self):
        # Built lazily so the DB/model registry exist before the pipeline
        # snapshots active weights.
        self._pipeline = None
        # Choose where signals come from: AURORA (with manual fallback) when
        # enabled and reachable, otherwise manual files.
        llm = None
        try:
            llm = get_client()
        except RuntimeError:
            pass
        self.signal_source, self.source_label = default_source(llm_client=llm)

    @property
    def pipeline(self) -> MeridianPipeline:
        if self._pipeline is None:
            self._pipeline = MeridianPipeline()
        return self._pipeline

    def cmd_scan(self, ticker: str):
        signals, error = self.signal_source.for_ticker(ticker)
        if error:
            console.print(f"[red]{error}[/red]")
            console.print(
                f"[dim]Provide manual signals at "
                f"{signal_file_path(ticker)} — a JSON array of signal dicts "
                f"(signal_type, direction, magnitude, confidence, source).[/dim]"
            )
            return

        scan = self.pipeline.run_entity(ticker, signals)
        render_scan(scan)

    def cmd_recommend(self):
        tickers = AssetUniverse().tickers()
        scans, skipped = self.pipeline.run_universe(tickers, source=self.signal_source)
        tlh = {}
        if SYNTRACKR_ENABLED:
            try:
                from integrations import syntrackr
                tlh = syntrackr.build_overlay(tickers, self._syntrackr_source())
            except Exception:
                tlh = {}
        render_recommend(scans, skipped, tlh=tlh)

    def _syntrackr_source(self):
        """Override point for a live Syntrackr client; mock used until wired."""
        from integrations.syntrackr import MockSyntrackrSource
        return MockSyntrackrSource()

    def cmd_build_portfolio(self):
        universe = AssetUniverse()
        scans, skipped = self.pipeline.run_universe(universe.tickers(), source=self.signal_source)
        if not scans:
            console.print("[yellow]No scored assets — cannot build a portfolio.[/yellow]")
            return

        results = [s.result for s in scans]
        decisions = [s.decision for s in scans]
        sector_map = {a["ticker"]: a["sector"] for a in universe.get_all()}

        constructor = PortfolioConstructor()
        portfolio = constructor.construct(results, decisions, sector_map=sector_map)
        constructor.save(portfolio)

        # Log every allocation for later outcome resolution (meta-learning).
        tracker = PerformanceTracker()
        for a in portfolio.allocations:
            tracker.log_decision(
                run_id=portfolio.run_id,
                ticker=a.ticker,
                classification=a.classification,
                acs=a.acs,
            )

        render_portfolio(portfolio)
        if skipped:
            console.print(f"[dim]{len(skipped)} asset(s) skipped (no signal file).[/dim]")

    def cmd_compare(self, ticker_a: str, ticker_b: str):
        signals_a, err_a = self.signal_source.for_ticker(ticker_a)
        signals_b, err_b = self.signal_source.for_ticker(ticker_b)
        if err_a:
            console.print(f"[red]{err_a}[/red]")
            return
        if err_b:
            console.print(f"[red]{err_b}[/red]")
            return
        scan_a = self.pipeline.run_entity(ticker_a, signals_a)
        scan_b = self.pipeline.run_entity(ticker_b, signals_b)
        render_compare(scan_a, scan_b)

    def cmd_scenarios(self):
        console.print("[bold]Available scenarios:[/bold]")
        for s in list_scenarios():
            console.print(f"  [cyan]{s.name}[/cyan] — {s.description} [dim]({s.regime})[/dim]")

    def cmd_scenario(self, name: str):
        scenario = get_scenario(name)
        if scenario is None:
            console.print(f"[red]Unknown scenario:[/red] {name}")
            self.cmd_scenarios()
            return

        universe = AssetUniverse()
        universe_data = []
        for asset in universe.get_all():
            signals, error = self.signal_source.for_ticker(asset["ticker"])
            if error:
                continue
            universe_data.append({
                "ticker": asset["ticker"],
                "sector": asset["sector"],
                "asset_class": asset["asset_class"],
                "signals": signals,
            })

        if not universe_data:
            console.print("[yellow]No assets with signals — cannot run a scenario.[/yellow]")
            return

        report = Simulator(pipeline=self.pipeline).run_scenario(scenario, universe_data)
        render_scenario(report)

    def _universe_scans(self):
        """Run the full active universe through the configured signal source."""
        return self.pipeline.run_universe(AssetUniverse().tickers(), source=self.signal_source)

    def cmd_brief(self):
        scans, skipped = self._universe_scans()
        if not scans:
            console.print("[yellow]No scored assets — provide signals to generate a brief.[/yellow]")
            return

        results = [s.result for s in scans]
        decisions = [s.decision for s in scans]
        prioritized = [s.prioritized for s in scans]
        regime = classify_current_regime(results)

        # Fire alerts for this run.
        alerts = AlertSystem()
        fired = sum(alerts.check_and_fire(s.result, s.prioritized) for s in scans)

        brief = daily_brief.generate(results, prioritized, decisions, regime=regime)

        # Persist to logs/ with a timestamp.
        Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        (Path(LOG_PATH) / f"brief_{stamp}.txt").write_text(brief)
        console.print(
            f"[dim]Saved to {LOG_PATH}/brief_{stamp}.txt · {fired} alert(s) fired"
            + (f" · {len(skipped)} skipped" if skipped else "") + "[/dim]"
        )

    def cmd_weekly(self):
        scans, _ = self._universe_scans()
        if not scans:
            console.print("[yellow]No scored assets — cannot generate a weekly summary.[/yellow]")
            return
        regime = classify_current_regime([s.result for s in scans])
        prior = weekly_summary.load_prior_snapshot()
        text = weekly_summary.generate(scans, regime, prior=prior)
        from rich.panel import Panel
        from rich import box as _box
        console.print(Panel(text, title="[bold cyan]MERIDIAN WEEKLY SUMMARY[/bold cyan]", box=_box.ROUNDED))
        console.print(f"[dim]Saved to {LOG_PATH}/[/dim]")

    def cmd_alerts(self):
        render_alerts(AlertSystem().get_active())

    def cmd_ack(self, alert_id: str):
        AlertSystem().acknowledge(alert_id)
        console.print(f"[green]Acknowledged[/green] {alert_id}")

    def cmd_resolve(self, ticker: str, actual_return: float):
        n = PerformanceTracker().resolve_ticker(ticker, actual_return)
        if n:
            console.print(f"[green]Resolved[/green] {n} outcome(s) for {ticker.upper()} at {actual_return:+.2%}")
        else:
            console.print(f"[yellow]No pending outcomes for {ticker.upper()}[/yellow]")

    def cmd_learn(self):
        result = WeightAdjuster().run_cycle()
        if result.adjusted:
            console.print(f"[green]Weights adjusted[/green] → model v{result.new_version}")
            console.print(f"  {result.reason}")
            console.print(f"  {result.old_weights}  →  {result.new_weights}")
            self._pipeline = None  # rebuild so new weights take effect
        else:
            console.print(f"[cyan]No adjustment:[/cyan] {result.reason}")

    def cmd_status(self):
        registry = ModelRegistry()
        active = registry.get_active()
        version = active["version"] if active else "none"
        weights = active["weights"] if active else {}
        thresholds = active["thresholds"] if active else {}
        accuracy = PerformanceTracker().get_accuracy_by_classification()
        history = registry.history()
        render_status(version, weights, thresholds, DB_PATH, accuracy, history)

    def cmd_universe(self):
        assets = AssetUniverse().get_all()
        console.print(f"[bold]Active universe — {len(assets)} assets[/bold]")
        for a in assets:
            has_signals = "" if signal_file_path(a["ticker"]).exists() else " [dim](no signals)[/dim]"
            console.print(f"  [bold]{a['ticker']:6s}[/bold] {a['name']:28s} [dim]{a['sector'] or '—'}[/dim]{has_signals}")

    def cmd_add(self, spec: str):
        try:
            parts = shlex.split(spec)   # honors quoted multi-word names
        except ValueError:
            parts = spec.split()
        if not parts:
            console.print("[red]Usage: meridian add <TICKER> [name] [sector][/red]")
            return
        ticker = parts[0].upper()
        name = parts[1] if len(parts) > 1 else ticker
        sector = parts[2] if len(parts) > 2 else None
        AssetUniverse().add(ticker, name, sector=sector)
        console.print(f"[green]Added[/green] {ticker} to the universe"
                      + (f" [dim]({sector})[/dim]" if sector else ""))

    def cmd_remove(self, ticker: str):
        AssetUniverse().remove(ticker.upper())
        console.print(f"[yellow]Removed[/yellow] {ticker.upper()} from the active universe")

    def cmd_ask(self, query: str):
        """Natural-language fallback — freeform analysis with current system context."""
        try:
            client = get_client()
        except RuntimeError as e:
            console.print(f"[red]Unknown command.[/red] {e}")
            console.print("[dim]Type [bold]help[/bold] for the command list.[/dim]")
            return

        registry = ModelRegistry()
        active = registry.get_active()
        version = active["version"] if active else "1.0.0"
        weights = active["weights"] if active else {}
        tickers = AssetUniverse().tickers()
        context = nl_fallback.build_context(version, weights, tickers)

        console.print("[dim]Analyzing…[/dim]")
        try:
            answer = nl_fallback.analyze(query, context, client)
        except Exception as e:  # surface API errors without crashing the REPL
            console.print(f"[red]Analyst error:[/red] {e}")
            return
        from rich.panel import Panel
        from rich import box as _box
        console.print(Panel(answer, title="[bold cyan]MERIDIAN ANALYST[/bold cyan]", box=_box.ROUNDED))


def main():
    parser = argparse.ArgumentParser(description="Meridian Financial Intelligence System")
    parser.add_argument("--brief", action="store_true", help="Run daily brief and exit")
    parser.add_argument("--status", action="store_true", help="Print system status and exit")
    args = parser.parse_args()

    console.print("[bold cyan]MERIDIAN[/bold cyan] — Initializing...")
    init_db()
    ensure_baseline_model()
    ensure_universe_seeded()

    core = MeridianCore()
    src_color = "green" if core.source_label == "AURORA" else "cyan"
    console.print(f"[{src_color}]Signal source:[/{src_color}] {core.source_label}")

    if args.status:
        core.cmd_status()
        return

    if args.brief:
        core.cmd_brief()
        return

    run_chat(core)


if __name__ == "__main__":
    main()
