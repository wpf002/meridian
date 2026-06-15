"""
Performance Tracker
-------------------
Logs every decision output against real-world outcomes.
Powers the meta-learning weight adjustment cycle.
"""

import uuid
import sqlite3
from datetime import datetime, timezone
from config.settings import DB_PATH


class PerformanceTracker:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def log_decision(
        self,
        run_id: str,
        ticker: str,
        classification: str,
        acs: float,
        outcome_period_days: int = 90,
    ) -> str:
        entry_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO decision_outcomes
                    (id, run_id, ticker, classification_at_time, acs_at_time, outcome_period_days, logged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_id, run_id, ticker, classification, acs,
                 outcome_period_days, datetime.now(timezone.utc).isoformat()),
            )
        return entry_id

    def resolve_outcome(self, entry_id: str, actual_return: float, correct: bool):
        """Called when the outcome period has elapsed and actual performance is known."""
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE decision_outcomes
                SET actual_return = ?, classification_correct = ?, resolved_at = ?
                WHERE id = ?
                """,
                (actual_return, 1 if correct else 0,
                 datetime.now(timezone.utc).isoformat(), entry_id),
            )

    def get_accuracy_by_classification(self) -> dict[str, dict]:
        """
        Returns accuracy stats per classification type.
        Only includes resolved outcomes.
        """
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT classification_at_time,
                       COUNT(*) as total,
                       SUM(classification_correct) as correct,
                       AVG(actual_return) as avg_return
                FROM decision_outcomes
                WHERE classification_correct IS NOT NULL
                GROUP BY classification_at_time
                """
            )
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()

        result = {}
        for row in rows:
            d = dict(zip(cols, row))
            classification = d["classification_at_time"]
            result[classification] = {
                "total": d["total"],
                "correct": int(d["correct"] or 0),
                "accuracy": round((d["correct"] or 0) / d["total"], 3),
                "avg_return": round(d["avg_return"] or 0.0, 4),
            }
        return result

    def get_pending(self) -> list[dict]:
        """Return all unresolved outcomes."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM decision_outcomes WHERE classification_correct IS NULL"
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
