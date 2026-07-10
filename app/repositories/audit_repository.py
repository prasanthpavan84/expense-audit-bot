import datetime

from app.memory.sqlite_db import db
from app.models.domain import Expense
from app.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository):
    """Repository handling persistence of Expense Audits in SQLite."""

    def __init__(self, database=None):
        self.db = database or db

    def save(self, expense: Expense) -> Expense:
        conn = self.db.connection
        cursor = conn.cursor()

        # Generate id if missing
        if not expense.id:
            expense.id = f"exp-{datetime.date.today().isoformat()}-{int(datetime.datetime.utcnow().timestamp())}"

        # Insert or Replace
        cursor.execute(
            """
            INSERT OR REPLACE INTO audits (
                id, user_id, status, decision, reasoning, total_amount, currency,
                policy_version, workflow_version, prompt_version, model_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                expense.id,
                expense.employee_id,
                expense.status,
                expense.status,  # Map decision to status
                "",  # Reasoning will be logged or stored separately if needed
                expense.amount,
                expense.currency,
                "v1",
                "v1",
                "v1",
                "gemini-2.5-flash",
                datetime.datetime.utcnow().isoformat() + "Z",
            ),
        )
        conn.commit()
        return expense

    def find_by_id(self, expense_id: str) -> Expense | None:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audits WHERE id = ?", (expense_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Expense(
            id=row["id"],
            employee_id=row["user_id"],
            merchant="Unknown",  # Loaded from metadata/events
            date="Unknown",
            amount=row["total_amount"],
            currency=row["currency"],
            status=row["status"],
            reimbursable=row["total_amount"] if row["status"] in ["Approved", "Approved with Exception"] else 0.0,
            rejected=row["total_amount"] if row["status"] == "Rejected" else 0.0,
        )

    def find_all(self) -> list[Expense]:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audits ORDER BY created_at DESC")
        rows = cursor.fetchall()
        expenses = []
        for row in rows:
            expenses.append(
                Expense(
                    id=row["id"],
                    employee_id=row["user_id"],
                    merchant="Unknown",
                    date="Unknown",
                    amount=row["total_amount"],
                    currency=row["currency"],
                    status=row["status"],
                )
            )
        return expenses

    def delete(self, expense_id: str) -> bool:
        conn = self.db.connection
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audits WHERE id = ?", (expense_id,))
        conn.commit()
        return cursor.rowcount > 0
