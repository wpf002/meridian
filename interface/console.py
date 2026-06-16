"""
Shared Console
--------------
A single Rich console for the whole interface, with recording enabled so a full
session transcript can be exported to the session log on exit.
"""

from rich.console import Console

console = Console(record=True)
