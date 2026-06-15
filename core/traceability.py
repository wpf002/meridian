"""
Traceability Kernel
-------------------
Records every output with full lineage.
Every decision Meridian produces can be traced back to its exact inputs.

Records:
  - Source signals used
  - Model version at time of output
  - Transformations applied
  - Rationale
  - Confidence
"""

import json
import uuid
import sqlite3
from datetime import datetime, timezone
from config.settings import DB_PATH

MODEL_VERSION = "1.0.0"


class TraceabilityKernel:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def log(
        self,
        action: str,
        entity: str = None,
        run_id: str = None,
        input_data: dict = None,
        output_data: dict = None,
    ) -> str:
        """
        Write an audit entry. Returns the log entry ID.
        """
        entry_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                    (id, action, entity, run_id, input_snapshot, output_snapshot, model_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    action,
                    entity,
                    run_id,
                    json.dumps(input_data) if input_data else None,
                    json.dumps(output_data) if output_data else None,
                    MODEL_VERSION,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return entry_id

    def get_trace(self, run_id: str) -> list[dict]:
        """Return all audit entries for a given run."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_log WHERE run_id = ? ORDER BY created_at ASC",
                (run_id,),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_entity_history(self, entity: str, limit: int = 50) -> list[dict]:
        """Return recent audit entries for a specific entity."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_log WHERE entity = ? ORDER BY created_at DESC LIMIT ?",
                (entity, limit),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
