"""
Asset Universe
--------------
Manages the dynamic set of assets Meridian tracks and scores.
Assets are stored in the database and can be added/removed at runtime.
"""

import sqlite3
from datetime import datetime, timezone
from config.settings import DB_PATH


class AssetUniverse:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def add(self, ticker: str, name: str, sector: str = None, asset_class: str = None, notes: str = None):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets (ticker, name, sector, asset_class, active, added_at, notes)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (ticker, name, sector, asset_class, datetime.now(timezone.utc).isoformat(), notes),
            )

    def remove(self, ticker: str):
        """Soft delete — sets active = 0."""
        with self._conn() as conn:
            conn.execute("UPDATE assets SET active = 0 WHERE ticker = ?", (ticker,))

    def get_all(self, active_only: bool = True) -> list[dict]:
        with self._conn() as conn:
            query = "SELECT * FROM assets"
            if active_only:
                query += " WHERE active = 1"
            cursor = conn.execute(query)
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get(self, ticker: str) -> dict | None:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM assets WHERE ticker = ?", (ticker,))
            cols = [d[0] for d in cursor.description]
            row = cursor.fetchone()
            return dict(zip(cols, row)) if row else None

    def tickers(self, active_only: bool = True) -> list[str]:
        return [a["ticker"] for a in self.get_all(active_only)]
