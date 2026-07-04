import json
from typing import List, Dict, Any
import datetime
from app.memory.sqlite_db import db

class EventRepository:
    """Repository handling persistence of workflow events for audit replay and explainability."""

    def __init__(self, database=None):
        self.db = database or db

    def save_event(
        self,
        audit_id: str,
        correlation_id: str,
        agent: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> None:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (audit_id, correlation_id, agent, event_type, payload, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            correlation_id,
            agent,
            event_type,
            json.dumps(payload),
            datetime.datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()

    def get_events_for_audit(self, audit_id: str) -> List[Dict[str, Any]]:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE audit_id = ? ORDER BY id ASC", (audit_id,))
        rows = cursor.fetchall()
        events = []
        for row in rows:
            events.append({
                "id": row["id"],
                "audit_id": row["audit_id"],
                "correlation_id": row["correlation_id"],
                "agent": row["agent"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload"]),
                "timestamp": row["timestamp"]
            })
        return events

    def get_all_events(self) -> List[Dict[str, Any]]:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY id ASC")
        rows = cursor.fetchall()
        events = []
        for row in rows:
            events.append({
                "id": row["id"],
                "audit_id": row["audit_id"],
                "correlation_id": row["correlation_id"],
                "agent": row["agent"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload"]),
                "timestamp": row["timestamp"]
            })
        return events
