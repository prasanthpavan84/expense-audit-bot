import sqlite3
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class ReviewQueue:
    """SQLite-backed queue for human review items."""

    def __init__(self, db_path: str = "review_queue.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_items (
                    id TEXT PRIMARY KEY,
                    raw_input TEXT,
                    risk_score REAL,
                    status TEXT,
                    created_at TEXT,
                    resolution TEXT,
                    reviewed_by TEXT,
                    reviewed_at TEXT
                )
            """)
            conn.commit()

    def push(self, item_id: str, raw_input: str, risk_score: float) -> None:
        """Push a new item onto the human review queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO review_items (id, raw_input, risk_score, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (item_id, raw_input, risk_score, "PENDING", datetime.utcnow().isoformat())
            )
            conn.commit()

    def pop(self, item_id: str, resolution: str, reviewer: str) -> None:
        """Resolve an item in the queue."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE review_items SET status = ?, resolution = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                ("RESOLVED", resolution, reviewer, datetime.utcnow().isoformat(), item_id)
            )
            conn.commit()

    def get_pending(self) -> List[Dict[str, Any]]:
        """Retrieve all pending items."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM review_items WHERE status = 'PENDING'")
            return [dict(row) for row in cursor.fetchall()]

    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all items (pending and resolved)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM review_items ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
