import datetime
import json
from typing import Any

from app.memory.sqlite_db import db


class CheckpointRepository:
    """Repository handling workflow checkpointing to recover from crashes or human pauses."""

    def __init__(self, database=None):
        self.db = database or db

    def save_checkpoint(
        self, audit_id: str, correlation_id: str, last_completed_step: str, state_data: dict[str, Any]
    ) -> None:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO checkpoints (audit_id, correlation_id, last_completed_step, state_data, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                audit_id,
                correlation_id,
                last_completed_step,
                json.dumps(state_data),
                datetime.datetime.utcnow().isoformat() + "Z",
            ),
        )
        conn.commit()

    def get_checkpoint(self, audit_id: str) -> dict[str, Any] | None:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM checkpoints WHERE audit_id = ?", (audit_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "audit_id": row["audit_id"],
            "correlation_id": row["correlation_id"],
            "last_completed_step": row["last_completed_step"],
            "state_data": json.loads(row["state_data"]),
            "updated_at": row["updated_at"],
        }

    def delete_checkpoint(self, audit_id: str) -> bool:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE audit_id = ?", (audit_id,))
        conn.commit()
        return cursor.rowcount > 0
