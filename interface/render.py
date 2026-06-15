"""
Terminal Rendering
------------------
Rich rendering for pipeline outputs. Kept separate from command dispatch
so the same renderers can be reused by recommend / compare / brief later.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.pipeline import ScanResult
from portfolio.constructor import Portfolio
from sandbox.simulator import ScenarioReport

console = Console()


_CLASSIFICATION_STYLE = {
    "CORE": "bold green",
    "HIGH-ASYMMETRY": "bold cyan",
    "TACTICAL": "bold yellow",
    "AVOID": "bold red",
}

_ACTION_STYLE = {
    "ESCALATE": "bold green",
    "MONITOR": "yellow",
    "RESTRICT": "bold red",
    "LOG": "dim",
}

_CONVICTION_STYLE = {"HIGH": "green", "MEDIUM": "yellow", "LOW": "red"}


def render_scan(scan: ScanResult) -> None:
    """Render a full single-asset scan: header, ACS breakdown, flags, rationale."""
    r = scan.result
    conf = scan.confidence

    cls_style = _CLASSIFICATION_STYLE.get(scan.classification, "white")
    action_style = _ACTION_STYLE.get(scan.decision.action, "white")
    conv_style = _CONVICTION_STYLE.get(conf["conviction"], "white")

    header = (
        f"[bold white]{scan.entity}[/bold white]   "
        f"ACS [bold]{r.acs:.3f}[/bold]   "
        f"[{cls_style}]{scan.classification}[/{cls_style}]   "
        f"Tier {scan.prioritized.tier}   "
        f"[{action_style}]{scan.decision.action}[/{action_style}]   "
        f"Conviction [{conv_style}]{conf['conviction']}[/{conv_style}]"
    )
    console.print(Panel(header, title="MERIDIAN SCAN", box=box.ROUNDED, expand=False))

    # ACS component breakdown
    weights = r.weights_used
    table = Table(box=box.SIMPLE_HEAVY, show_edge=False)
    table.add_column("Component", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right", style="dim")
    table.add_row("Macro Alignment (MAS)", f"{r.mas:.3f}", f"{weights.get('macro', 0):.2f}")
    table.add_row("Tactical Alignment (TAS)", f"{r.tas:.3f}", f"{weights.get('tactical', 0):.2f}")
    table.add_row("Sentiment Alignment (SAS)", f"{r.sas:.3f}", f"{weights.get('sentiment', 0):.2f}")
    table.add_row(
        "Structural Risk (SRS)",
        f"[red]-{r.srs:.3f}[/red]",
        f"{weights.get('structural_risk', 0):.2f}",
    )
    table.add_row("[bold]Composite (ACS)[/bold]", f"[bold]{r.acs:.3f}[/bold]", "")
    console.print(table)

    # Confidence / signal context
    console.print(
        f"  Signals: [bold]{r.signal_count}[/bold]   "
        f"Avg confidence: [bold]{r.confidence:.2f}[/bold]   "
        f"Signal agreement: [bold]{conf['signal_agreement']:.2f}[/bold]   "
        f"Model: [dim]v{scan.model_version}[/dim]"
    )

    # Flags
    if scan.decision.flags:
        flag_str = "  ".join(f"[yellow]⚑ {f}[/yellow]" for f in scan.decision.flags)
        console.print(f"  {flag_str}")

    if scan.decision.override_reason:
        console.print(f"  [magenta]Override:[/magenta] {scan.decision.override_reason}")

    # Notes from the scoring engine (e.g. high-risk review flag)
    for note in r.notes:
        console.print(f"  [dim]· {note}[/dim]")

    # Dropped signals
    if scan.harmonize_errors:
        console.print(
            f"  [red]{len(scan.harmonize_errors)} signal(s) rejected during harmonization[/red]"
        )

    console.print(f"\n  [dim]Rationale:[/dim] {scan.rationale}")
    console.print(f"  [dim]run_id: {scan.run_id}[/dim]\n")


def _cls(classification: str) -> str:
    style = _CLASSIFICATION_STYLE.get(classification, "white")
    return f"[{style}]{classification}[/{style}]"


def _conv(label: str) -> str:
    style = _CONVICTION_STYLE.get(label, "white")
    return f"[{style}]{label}[/{style}]"


def _report_skipped(skipped: list) -> None:
    if skipped:
        names = ", ".join(t for t, _ in skipped)
        console.print(
            f"[dim]{len(skipped)} asset(s) skipped (no signal file): {names}[/dim]\n"
        )


def render_recommend(scans: list[ScanResult], skipped: list = None) -> None:
    """Ranked universe table: rank, ticker, ACS, tier, classification, conviction, flags."""
    if not scans:
        console.print("[yellow]No assets scored — provide signal files for the universe.[/yellow]")
        _report_skipped(skipped or [])
        return

    table = Table(title="MERIDIAN — Universe Recommendations", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Ticker", style="bold")
    table.add_column("ACS", justify="right")
    table.add_column("Tier", justify="center")
    table.add_column("Classification")
    table.add_column("Conviction")
    table.add_column("Action")
    table.add_column("Flags", style="yellow")

    for i, s in enumerate(scans, start=1):
        action_style = _ACTION_STYLE.get(s.decision.action, "white")
        table.add_row(
            str(i),
            s.entity,
            f"{s.result.acs:.3f}",
            str(s.prioritized.tier),
            _cls(s.classification),
            _conv(s.confidence["conviction"]),
            f"[{action_style}]{s.decision.action}[/{action_style}]",
            ", ".join(s.decision.flags) if s.decision.flags else "[dim]—[/dim]",
        )

    console.print(table)
    _report_skipped(skipped or [])


def render_portfolio(portfolio: Portfolio) -> None:
    """Sleeve allocation table grouped by sleeve, with per-sleeve and total weights."""
    sleeves = portfolio.by_sleeve()
    if not portfolio.allocations:
        console.print("[yellow]No assets qualified for portfolio construction.[/yellow]")
        return

    console.print(Panel(f"MERIDIAN PORTFOLIO  ·  run {portfolio.run_id}", box=box.ROUNDED, expand=False))

    sleeve_order = ["core", "growth", "defensive", "tactical"]
    ordered = [s for s in sleeve_order if s in sleeves] + [s for s in sleeves if s not in sleeve_order]

    for sleeve in ordered:
        allocs = sorted(sleeves[sleeve], key=lambda a: a.weight, reverse=True)
        sleeve_weight = sum(a.weight for a in allocs)
        table = Table(
            title=f"{sleeve.upper()} sleeve  ·  {sleeve_weight*100:.1f}%",
            box=box.SIMPLE, title_justify="left",
        )
        table.add_column("Ticker", style="bold")
        table.add_column("Weight", justify="right")
        table.add_column("ACS", justify="right")
        table.add_column("Classification")
        for a in allocs:
            table.add_row(a.ticker, f"{a.weight*100:.2f}%", f"{a.acs:.3f}", _cls(a.classification))
        console.print(table)

    console.print(f"  [bold]Total allocated:[/bold] {portfolio.total_weight()*100:.1f}%")
    for w in portfolio.warnings:
        console.print(f"  [yellow]⚠ {w}[/yellow]")
    console.print()


def render_compare(scan_a: ScanResult, scan_b: ScanResult) -> None:
    """Side-by-side ACS component breakdown for two assets."""
    a, b = scan_a.result, scan_b.result

    table = Table(title=f"MERIDIAN COMPARE — {scan_a.entity} vs {scan_b.entity}", box=box.SIMPLE_HEAVY)
    table.add_column("Component", style="cyan")
    table.add_column(scan_a.entity, justify="right")
    table.add_column(scan_b.entity, justify="right")
    table.add_column("Δ", justify="right", style="dim")

    def row(label, va, vb):
        table.add_row(label, f"{va:.3f}", f"{vb:.3f}", f"{va - vb:+.3f}")

    row("Macro (MAS)", a.mas, b.mas)
    row("Tactical (TAS)", a.tas, b.tas)
    row("Sentiment (SAS)", a.sas, b.sas)
    row("Structural Risk (SRS)", a.srs, b.srs)
    row("Composite (ACS)", a.acs, b.acs)
    table.add_row(
        "Classification",
        _cls(scan_a.classification),
        _cls(scan_b.classification),
        "",
    )
    table.add_row(
        "Conviction",
        _conv(scan_a.confidence["conviction"]),
        _conv(scan_b.confidence["conviction"]),
        "",
    )
    console.print(table)
    console.print()


def _delta(value: float) -> str:
    """Color a signed delta: green up, red down."""
    if value > 0.0005:
        return f"[green]{value:+.3f}[/green]"
    if value < -0.0005:
        return f"[red]{value:+.3f}[/red]"
    return f"[dim]{value:+.3f}[/dim]"


def render_scenario(report: ScenarioReport) -> None:
    """Render a full scenario impact report: header, per-entity table, sleeve drawdown."""
    pb, ps = report.portfolio_baseline_acs, report.portfolio_base_acs
    header = (
        f"[bold white]{report.scenario_name}[/bold white]\n"
        f"Stressed regime: [yellow]{report.scenario_regime}[/yellow]   "
        f"Current regime (inferred): [cyan]{report.current_regime}[/cyan]\n"
        f"Portfolio ACS (avg): {pb:.3f} → {ps:.3f}   {_delta(ps - pb)}   "
        f"Classification downgrades: [red]{report.downgrades}[/red]"
    )
    console.print(Panel(header, title="MERIDIAN SCENARIO", box=box.ROUNDED, expand=False))

    # Per-entity impact (sorted by base-case delta, worst hit first)
    table = Table(title="Per-asset impact", box=box.SIMPLE_HEAVY)
    table.add_column("Ticker", style="bold")
    table.add_column("Sleeve", style="dim")
    table.add_column("Base ACS", justify="right")
    table.add_column("→ Scenario", justify="right")
    table.add_column("Δ (base)", justify="right")
    table.add_column("Best / Worst", justify="center")
    table.add_column("Classification", justify="center")

    for e in sorted(report.entities, key=lambda x: x.acs_delta):
        cls_cell = _cls(e.baseline_classification)
        if e.classification_changed:
            cls_cell += f" → {_cls(e.scenario_classification)}"
        table.add_row(
            e.entity,
            e.sleeve,
            f"{e.baseline_acs:.3f}",
            f"{e.base_acs:.3f}",
            _delta(e.acs_delta),
            f"[green]{e.best_acs:.2f}[/green] / [red]{e.worst_acs:.2f}[/red]",
            cls_cell,
        )
    console.print(table)

    # Sleeve drawdown
    sleeve_tbl = Table(title="Sleeve drawdown (worst case)", box=box.SIMPLE, title_justify="left")
    sleeve_tbl.add_column("Sleeve", style="bold")
    sleeve_tbl.add_column("Assets", justify="right")
    sleeve_tbl.add_column("Avg Δ (base)", justify="right")
    sleeve_tbl.add_column("Worst drawdown", justify="right")
    for s in report.sleeve_impacts:
        sleeve_tbl.add_row(
            s.sleeve.capitalize(),
            str(s.asset_count),
            _delta(s.avg_base_delta),
            _delta(s.worst_drawdown),
        )
    console.print(sleeve_tbl)
    console.print(f"  [dim]run_id: {report.run_id}[/dim]\n")


_SEVERITY_STYLE = {"high": "bold red", "medium": "yellow", "low": "dim"}


def render_alerts(alerts: list) -> None:
    """Active alert table with severity coloring."""
    if not alerts:
        console.print("[green]No active alerts.[/green]\n")
        return

    table = Table(title=f"MERIDIAN ALERTS — {len(alerts)} active", box=box.SIMPLE_HEAVY)
    table.add_column("Severity")
    table.add_column("Type", style="cyan")
    table.add_column("Entity", style="bold")
    table.add_column("Message")
    table.add_column("ID", style="dim")

    order = {"high": 0, "medium": 1, "low": 2}
    for a in sorted(alerts, key=lambda x: order.get(x["severity"], 9)):
        style = _SEVERITY_STYLE.get(a["severity"], "white")
        table.add_row(
            f"[{style}]{a['severity'].upper()}[/{style}]",
            a["alert_type"],
            a["entity"] or "—",
            a["message"],
            a["id"][:8],
        )
    console.print(table)
    console.print("[dim]Acknowledge with: meridian ack <ID>[/dim]\n")


def render_status(version: str, weights: dict, thresholds: dict, db_path: str,
                  accuracy: dict, model_history: list) -> None:
    """System status: model version, weights/thresholds, accuracy, weight history."""
    console.print(Panel(
        f"[bold]Model[/bold] v{version}    [dim]{db_path}[/dim]",
        title="MERIDIAN STATUS", box=box.ROUNDED, expand=False,
    ))

    wt = Table(box=box.SIMPLE, title="Active weights & thresholds", title_justify="left")
    wt.add_column("Weights", style="cyan")
    wt.add_column("", justify="right")
    for k, v in weights.items():
        wt.add_row(k, f"{v:.2f}")
    for k, v in thresholds.items():
        wt.add_row(f"[dim]threshold:{k}[/dim]", f"{v:.2f}")
    console.print(wt)

    if accuracy:
        acc = Table(box=box.SIMPLE, title="Accuracy by classification", title_justify="left")
        acc.add_column("Classification", style="bold")
        acc.add_column("Accuracy", justify="right")
        acc.add_column("Resolved", justify="right")
        acc.add_column("Avg return", justify="right")
        for cls, s in accuracy.items():
            acc.add_row(cls, f"{s['accuracy']:.0%}", f"{s['correct']}/{s['total']}", f"{s['avg_return']:+.2%}")
        console.print(acc)
    else:
        console.print("[dim]No resolved outcomes yet — accuracy unavailable.[/dim]")

    if model_history and len(model_history) > 1:
        hist = Table(box=box.SIMPLE, title="Model version history", title_justify="left")
        hist.add_column("Version", style="bold")
        hist.add_column("Notes")
        for m in model_history[:6]:
            hist.add_row(m["version"], (m.get("notes") or "")[:60])
        console.print(hist)
    console.print()
