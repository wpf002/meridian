"""
Alert System
------------
Fires alerts when thresholds are breached, risk spikes,
signal divergences occur, or classifications change.
"""

import uuid
import sqlite3
from datetime import datetime, timezone
from config.settings import DB_PATH, ALERT_THRESHOLDS
from core.scoring_engine import ACSResult
from core.priority_engine import PrioritizedEntity


class AlertSystem:

    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"

    def __init__(self, db_path: str = DB_PATH, thresholds: dict = None):
        self.db_path = db_path
        self.thresholds = thresholds or ALERT_THRESHOLDS.copy()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _fire(self, alert_type: str, entity: str, message: str, severity: str):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO alerts (id, alert_type, entity, message, severity, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), alert_type, entity, message, severity,
                 datetime.now(timezone.utc).isoformat()),
            )

    def check_and_fire(self, result: ACSResult, prioritized: PrioritizedEntity) -> int:
        """Evaluate one entity against thresholds, firing alerts. Returns count fired."""
        fired = 0

        # High structural risk
        if result.srs > self.thresholds["srs_high"]:
            self._fire(
                "risk_spike", result.entity,
                f"{result.entity}: Structural risk at {result.srs:.2f} — immediate review required",
                self.SEVERITY_HIGH,
            )
            fired += 1

        # Signal divergence
        if "MACRO/TACTICAL_DIVERGENCE" in prioritized.flags or "TACTICAL/MACRO_DIVERGENCE" in prioritized.flags:
            self._fire(
                "divergence", result.entity,
                f"{result.entity}: Macro/Tactical signal divergence detected",
                self.SEVERITY_MEDIUM,
            )
            fired += 1

        # Tier 1 threshold breach
        if prioritized.tier == 1 and result.acs >= self.thresholds["acs_tier_1"]:
            self._fire(
                "threshold_breach", result.entity,
                f"{result.entity}: ACS {result.acs:.3f} — Tier 1 threshold reached",
                self.SEVERITY_HIGH,
            )
            fired += 1

        # Low conviction on an otherwise actionable name
        if result.confidence < self.thresholds["confidence_low"] and prioritized.tier <= 2:
            self._fire(
                "low_confidence", result.entity,
                f"{result.entity}: Confidence {result.confidence:.2f} below threshold on a Tier {prioritized.tier} name",
                self.SEVERITY_LOW,
            )
            fired += 1

        return fired

    def get_active(self, acknowledged: bool = False) -> list[dict]:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM alerts WHERE acknowledged = ? ORDER BY created_at DESC",
                (1 if acknowledged else 0,),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def acknowledge(self, alert_id: str):
        with self._conn() as conn:
            conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
