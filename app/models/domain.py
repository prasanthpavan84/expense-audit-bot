import datetime
from typing import Any

from pydantic import BaseModel, Field


class Employee(BaseModel):
    id: str = "EMP102"
    name: str = "John Doe"
    department: str = "Engineering"
    role: str = "Associate"  # Associate, Manager, Executive


class Vendor(BaseModel):
    name: str
    is_restricted: bool = False
    categories: list[str] = Field(default_factory=list)


class ExtractedField(BaseModel):
    value: Any
    confidence: float = 1.0
    validation_status: str = "VALID"
    source: str = "LLM"
    reason: str = ""


class Receipt(BaseModel):
    raw_text: str = ""
    ocr_confidence_score: float = 1.0
    readability_issues: list[str] = Field(default_factory=list)
    manipulated_receipt: bool = False
    merchant_name: str = "Unknown"
    date: str = "Unknown"
    amount: float = 0.0
    currency: str = "USD"
    items: list[str] = Field(default_factory=list)
    category: str = "Other"
    merchant_provenance: ExtractedField | None = None
    date_provenance: ExtractedField | None = None
    amount_provenance: ExtractedField | None = None
    currency_provenance: ExtractedField | None = None


class Policy(BaseModel):
    version: str = "v1"
    category_limits: dict[str, float] = Field(default_factory=dict)
    restricted_vendors: list[str] = Field(default_factory=list)
    effective_date: str = "2026-01-01"
    expiration_date: str | None = None


class FraudSignal(BaseModel):
    score: float = 0.0
    indicators: list[str] = Field(default_factory=list)
    explanation: str = ""


class DecisionTrace(BaseModel):
    correlation_id: str
    agent_name: str
    state: str  # CREATED, RUNNING, WAITING_TOOL, COMPLETED, FAILED, RETRY, CANCELLED
    decision: str
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    latency_ms: float = 0.0


class Evidence(BaseModel):
    source: str
    field: str
    value: Any
    confidence: float
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    origin_agent: str = "unknown"
    validated: bool = False


class Expense(BaseModel):
    id: str | None = None
    employee_id: str = "EMP102"
    merchant: str
    date: str
    amount: float
    currency: str = "USD"
    category: str = "Other"
    items: list[str] = Field(default_factory=list)
    status: str = "Pending"  # Pending, Approved, Rejected, Needs Human Review
    reimbursable: float = 0.0
    rejected: float = 0.0
    fraud_score: float = 0.0


class AuditResult(BaseModel):
    is_approved: bool = False
    reason: str = ""
    fraud_score: float = 0.0
    policy_violations: list[str] = Field(default_factory=list)
    reasoning_trace: str = ""
    evidence_links: list[str] = Field(default_factory=list)
