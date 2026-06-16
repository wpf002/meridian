"""
Session History
---------------
Records every command issued during a chat session and, on exit, writes a
timestamped transcript to logs/ — the list of commands plus the full recorded
console output (tables, panels, analysis).
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from config.settings import LOG_PATH


class SessionHistory:

    def __init__(self):
        self.session_id = uuid.uuid4().hex[:8]
        self.started_at = datetime.now(timezone.utc)
        self.commands: list[tuple[str, str]] = []   # (iso_timestamp, command)

    def record(self, command: str) -> None:
        self.commands.append((datetime.now(timezone.utc).isoformat(), command))

    def save(self, console) -> str:
        """Write the session transcript to logs/ and return the file path."""
        Path(LOG_PATH).mkdir(parents=True, exist_ok=True)
        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        path = Path(LOG_PATH) / f"session_{stamp}_{self.session_id}.log"

        lines = [
            f"MERIDIAN SESSION {self.session_id}",
            f"Started: {self.started_at.isoformat()}",
            f"Commands: {len(self.commands)}",
            "",
            "=== COMMAND LOG ===",
        ]
        for ts, cmd in self.commands:
            lines.append(f"  {ts}  {cmd}")
        lines += ["", "=== TRANSCRIPT ===", console.export_text()]

        path.write_text("\n".join(lines))
        return str(path)
