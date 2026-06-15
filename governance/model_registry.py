"""
Model Registry
--------------
Tracks scoring weight versions.
Every weight change is versioned and logged.
"""

import uuid
import json
import sqlite3
from datetime import datetime, timezone
from config.settings import DB_PATH, SCORING_WEIGHTS, PRIORITY_THRESHOLDS


class ModelRegistry:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def register(self, version: str, weights: dict = None, thresholds: dict = None, notes: str = "") -> str:
        entry_id = str(uuid.uuid4())
        with self._conn() as conn:
            # Deactivate current active version
            conn.execute("UPDATE model_registry SET active = 0")
            conn.execute(
                """
                INSERT INTO model_registry (id, version, weights, thresholds, notes, active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    entry_id,
                    version,
                    json.dumps(weights or SCORING_WEIGHTS),
                    json.dumps(thresholds or PRIORITY_THRESHOLDS),
                    notes,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return entry_id

    def get_active(self) -> dict | None:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM model_registry WHERE active = 1 LIMIT 1")
            cols = [d[0] for d in cursor.description]
            row = cursor.fetchone()
            if not row:
                return None
            result = dict(zip(cols, row))
            result["weights"] = json.loads(result["weights"])
            result["thresholds"] = json.loads(result["thresholds"])
            return result

    def history(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM model_registry ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
