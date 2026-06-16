"""
Performance Tracker
-------------------
Logs every decision output against real-world outcomes.
Powers the meta-learning weight adjustment cycle.
"""

import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from config.settings import DB_PATH, OUTCOME_PERIOD_DAYS


def _parse_dt(value) -> datetime:
    """Parse an ISO timestamp (with or without tz / fractional seconds) to UTC."""
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            dt = datetime.fromisoformat(s.split(".")[0].split("+")[0])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _nearest_close(points: list[tuple], target: datetime):
    """Closing price of the price point nearest `target` (points sorted by date)."""
    if not points:
        return None
    return min(points, key=lambda p: abs((p[0] - target).total_seconds()))[1]


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

    def snapshot_decisions(self, items: list[dict]) -> int:
        """
        Record today's calls so they can be graded later — idempotent per ticker
        per day, so it's safe to call on every universe scan / page view. Each
        item: {run_id, ticker, classification, acs}. Returns how many were newly
        logged.
        """
        if not items:
            return 0
        with self._conn() as conn:
            logged_today = {
                row[0] for row in conn.execute(
                    "SELECT DISTINCT ticker FROM decision_outcomes "
                    "WHERE date(logged_at) = date('now')"
                ).fetchall()
            }
        new = 0
        for it in items:
            ticker = it["ticker"].upper()
            if ticker in logged_today:
                continue
            self.log_decision(
                it["run_id"], ticker, it["classification"], it["acs"],
                it.get("outcome_period_days", OUTCOME_PERIOD_DAYS),
            )
            logged_today.add(ticker)
            new += 1
        return new

    def count_pending(self) -> int:
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM decision_outcomes WHERE classification_correct IS NULL"
            ).fetchone()[0]

    def resolve_due(self, price_lookup, now: datetime = None) -> int:
        """
        Auto-grade every pending call whose outcome window has elapsed, using
        realized prices. `price_lookup(ticker)` returns a list of (timestamp,
        close) points covering the window. A non-AVOID call is 'correct' if the
        return over the window was positive; AVOID is 'correct' if it wasn't.
        Calls whose window hasn't elapsed (or with no price data) are left
        pending. Returns how many were resolved.
        """
        now = now or datetime.now(timezone.utc)
        resolved = 0
        for p in self.get_pending():
            try:
                entry_dt = _parse_dt(p["logged_at"])
            except Exception:
                continue
            period = p.get("outcome_period_days") or OUTCOME_PERIOD_DAYS
            due_dt = entry_dt + timedelta(days=period)
            if now < due_dt:
                continue  # still within the holding window — not gradable yet

            points = []
            for ts, close in (price_lookup(p["ticker"]) or []):
                try:
                    points.append((_parse_dt(ts), float(close)))
                except Exception:
                    continue
            if len(points) < 2:
                continue
            points.sort(key=lambda x: x[0])

            entry_close = _nearest_close(points, entry_dt)
            exit_close = _nearest_close(points, due_dt)
            if not entry_close or not exit_close:
                continue

            actual_return = exit_close / entry_close - 1.0
            was_bullish = p["classification_at_time"] != "AVOID"
            correct = was_bullish == (actual_return > 0)
            self.resolve_outcome(p["id"], round(actual_return, 4), correct)
            resolved += 1
        return resolved

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

    def resolve_ticker(self, ticker: str, actual_return: float) -> int:
        """
        Resolve all pending outcomes for a ticker with a realized return.
        A non-AVOID call is 'correct' if the return was positive; AVOID is
        'correct' if the return was non-positive. Returns how many were resolved.
        """
        pending = [p for p in self.get_pending() if p["ticker"] == ticker.upper()]
        for p in pending:
            was_bullish = p["classification_at_time"] != "AVOID"
            correct = was_bullish == (actual_return > 0)
            self.resolve_outcome(p["id"], actual_return, correct)
        return len(pending)

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
