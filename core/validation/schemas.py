from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from domain.fraud import FraudResult
from domain.policy import PolicyResult
from domain.receipt import Receipt
from domain.report import Report


class ExecutionToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_id: str
    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class DecisionTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_name: str
    decision: str
    confidence: float
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class WorkflowContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    input: str
    intent: str = ""
    entities: dict[str, Any] = Field(default_factory=dict)
    receipt: Receipt | None = None
    ocr_result: str | None = None
    validation: Any | None = None
    policy_res: PolicyResult | None = None
    fraud_res: FraudResult | None = None
    report: Report | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    decision_traces: list[DecisionTrace] = Field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def set(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class AgentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str  # SUCCESS, FAILED, RETRY, ESCALATED
    output: Any
    confidence: float = 1.0
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == "SUCCESS"


class WorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str  # COMPLETED, FAILED, WAITING_FOR_REVIEW
    output: Any
    trace: list[DecisionTrace] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
