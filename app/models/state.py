import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExpenseItem(BaseModel):
    category: str = ""
    amount: float = 0.0
    currency: str = "USD"
    date: str = ""
    description: str = ""
    merchant: str = ""
    confidence_score: float = 1.0  # default to high confidence

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        if v and not re.match(r"^[a-zA-Z]{3}$", v) and v not in ["₹", "$", "€", "£", "Unknown"]:
            raise ValueError(f"Invalid currency code: {v}")
        return v.upper() if v else "USD"

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        if v and v.lower() != "unknown":
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                raise ValueError(f"Date '{v}' must be in YYYY-MM-DD format")
        return v


class AuditResult(BaseModel):
    is_approved: bool = False
    reason: str = ""
    fraud_score: float = 0.0
    policy_violations: list[str] = Field(default_factory=list)
    reasoning_trace: str = ""
    evidence_links: list[str] = Field(default_factory=list)


class WorkflowState(BaseModel):
    status: str = ""
    intent: str = ""
    expenses: list[ExpenseItem] = Field(default_factory=list)
    audit_results: dict[str, AuditResult] = Field(default_factory=dict)
    raw_input: str = ""
    report_format: str = "markdown"
    metadata: dict[str, Any] = Field(default_factory=dict)
    _history: list[dict[str, Any]] = []

    def create_snapshot(self):
        """Creates a snapshot of the current state and appends to history."""
        self._history.append(self.model_dump())

    def restore_snapshot(self):
        """Restores the state to the last snapshot if one exists."""
        if not self._history:
            return
        last_state = self._history.pop()
        for key, value in last_state.items():
            setattr(self, key, value)
