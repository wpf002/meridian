"""
Conversational Interface
------------------------
Chat-driven entry point for Meridian.

Supported commands:
  meridian scan <TICKER>       — Score and classify a single asset
  meridian recommend           — Top-ranked assets from active universe
  meridian build portfolio     — Construct full sleeve allocation
  meridian compare <A> vs <B>  — Side-by-side ACS breakdown
  meridian brief               — Daily intelligence brief
  meridian alerts              — Active unacknowledged alerts
  meridian status              — System status and model version
  help                         — Show this menu
  exit / quit                  — Exit
"""

import uuid
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def print_help():
    console.print("""
[bold cyan]MERIDIAN[/bold cyan] — Financial Intelligence System

[bold]Commands:[/bold]
  meridian scan <TICKER>        Score and classify an asset
  meridian recommend            Top-ranked assets
  meridian build portfolio      Construct portfolio allocation
  meridian compare <A> vs <B>   Compare two assets
  meridian brief                Daily intelligence brief
  meridian alerts               Active alerts
  meridian status               System status
  help                          Show this menu
  exit                          Quit
""")


def run_chat(meridian_core):
    """
    Main REPL loop. Accepts a MeridianCore instance that handles command dispatch.
    """
    console.print("[bold cyan]MERIDIAN[/bold cyan] Intelligence System — Online")
    console.print("Type [bold]help[/bold] for commands.\n")

    while True:
        try:
            raw = input("meridian> ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended.[/yellow]")
            break

        if not raw:
            continue

        cmd = raw.lower()

        if cmd in ("exit", "quit"):
            console.print("[yellow]Session ended.[/yellow]")
            break

        elif cmd == "help":
            print_help()

        elif cmd.startswith("meridian scan "):
            ticker = raw.split(" ")[-1].upper()
            meridian_core.cmd_scan(ticker)

        elif cmd == "meridian recommend":
            meridian_core.cmd_recommend()

        elif cmd == "meridian build portfolio":
            meridian_core.cmd_build_portfolio()

        elif cmd.startswith("meridian compare ") and " vs " in cmd:
            parts = raw.lower().replace("meridian compare ", "").split(" vs ")
            if len(parts) == 2:
                meridian_core.cmd_compare(parts[0].strip().upper(), parts[1].strip().upper())
            else:
                console.print("[red]Usage: meridian compare <TICKER_A> vs <TICKER_B>[/red]")

        elif cmd == "meridian brief":
            meridian_core.cmd_brief()

        elif cmd == "meridian alerts":
            meridian_core.cmd_alerts()

        elif cmd == "meridian status":
            meridian_core.cmd_status()

        else:
            console.print(f"[red]Unknown command:[/red] {raw}. Type [bold]help[/bold] for options.")
