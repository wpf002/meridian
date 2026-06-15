"""
Daily Brief
-----------
Generates a structured daily intelligence report.
Includes market overview, key signal changes, risk developments, and watchlist.
"""

from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.scoring_engine import ACSResult
from core.priority_engine import PrioritizedEntity
from classification.classifier import classify_batch
from core.decision_logic import DecisionOutput

console = Console()


def generate(
    results: list[ACSResult],
    prioritized: list[PrioritizedEntity],
    decisions: list[DecisionOutput],
    regime: str = "UNKNOWN",
) -> str:
    """
    Generates and prints the daily brief.
    Returns the brief as a plain text string.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    classifications = classify_batch(results, decisions)
    result_map = {r.entity: r for r in results}

    lines = [
        f"MERIDIAN DAILY BRIEF — {now}",
        f"Macro Regime: {regime}",
        "",
        "=== TIER 1 — IMMEDIATE ===",
    ]

    tier_1 = [p for p in prioritized if p.tier == 1]
    if tier_1:
        for p in tier_1:
            r = result_map.get(p.entity)
            cl = classifications.get(p.entity, "—")
            lines.append(
                f"  {p.entity:8s} | ACS: {p.acs:.3f} | {cl:15s} | Confidence: {p.confidence:.2f}"
                + (f" | FLAGS: {', '.join(p.flags)}" if p.flags else "")
            )
    else:
        lines.append("  None")

    lines += ["", "=== TIER 2 — MONITOR ==="]
    tier_2 = [p for p in prioritized if p.tier == 2]
    if tier_2:
        for p in tier_2:
            cl = classifications.get(p.entity, "—")
            lines.append(f"  {p.entity:8s} | ACS: {p.acs:.3f} | {cl:15s}")
    else:
        lines.append("  None")

    lines += ["", "=== RISK DEVELOPMENTS ==="]
    high_risk = [r for r in results if r.srs > 0.65]
    if high_risk:
        for r in high_risk:
            lines.append(f"  {r.entity}: Structural Risk {r.srs:.3f}")
    else:
        lines.append("  No elevated structural risk detected")

    lines += ["", "=== SIGNAL SUMMARY ==="]
    for r in results[:5]:  # Top 5 by ACS
        lines.append(
            f"  {r.entity}: MAS={r.mas:.2f} TAS={r.tas:.2f} SAS={r.sas:.2f} SRS={r.srs:.2f}"
        )

    brief = "\n".join(lines)
    console.print(Panel(brief, title="[bold cyan]MERIDIAN DAILY BRIEF[/bold cyan]", box=box.ROUNDED))
    return brief
