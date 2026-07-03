from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from domain.receipt import Receipt
from domain.policy import PolicyResult
from domain.fraud import FraudResult
from domain.report import Report


class ExecutionToken(BaseModel):
    token_id: str
    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        frozen = True


class DecisionTrace(BaseModel):
    agent_name: str
    decision: str
    confidence: float
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        frozen = True


class WorkflowContext(BaseModel):
    input: str
    intent: str = ""
    entities: Dict[str, Any] = Field(default_factory=dict)
    receipt: Optional[Receipt] = None
    ocr_result: Optional[str] = None
    validation: Optional[Any] = None
    policy_res: Optional[PolicyResult] = None
    fraud_res: Optional[FraudResult] = None
    report: Optional[Report] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    decision_traces: List[DecisionTrace] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    status: str  # SUCCESS, FAILED, RETRY, ESCALATED
    output: Any
    confidence: float = 1.0
    explanation: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True

    @property
    def success(self) -> bool:
        return self.status == "SUCCESS"



class WorkflowResult(BaseModel):
    status: str  # COMPLETED, FAILED, WAITING_FOR_REVIEW
    output: Any
    trace: List[DecisionTrace] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
