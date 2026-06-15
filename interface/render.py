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
