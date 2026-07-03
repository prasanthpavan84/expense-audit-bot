import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .validator import ValidationError
from .fraud import FraudEngine
from .policy import PolicyEngine


@dataclass
class DecisionTrace:
    """Tracks the sequential steps and results of the audit pipeline."""
    audit_id: str
    validation_errors: List[ValidationError] = field(default_factory=list)
    fraud_result: Dict[str, Any] = field(default_factory=dict)
    policy_result: Dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    """Orchestrates validation, fraud detection, and policy enforcement steps."""

    def __init__(self) -> None:
        self.fraud_engine = FraudEngine()
        self.policy_engine = PolicyEngine()

    def run(self, expense):
        """Execute the full audit pipeline for a single expense.
        Returns a dict with audit_id, decision, reasons, confidence, and trace.
        """
        audit_id = str(uuid.uuid4())
        trace = DecisionTrace(audit_id=audit_id)
        # Assume expense already validated
        validated_expense = expense
        # Fraud detection (using empty recent list and zero average for now)
        fraud_output = self.fraud_engine.run(validated_expense, [], 0.0)
        trace.fraud_result = fraud_output
        # Policy enforcement
        policy_output = self.policy_engine.evaluate(validated_expense)
        trace.policy_result = policy_output
        # Decision logic
        decision = "approved"
        confidence = 1.0
        reasons: Dict[str, Any] = {}
        
        # Fraud checks return a dict of checks. Let's see if any check is True.
        # fraud_output is Dict[str, bool] from run_fraud_checks.
        # e.g., {'duplicate_receipt': bool, 'split_expense': bool, 'amount_anomaly': bool}
        is_fraudulent = any(fraud_output.values())
        if is_fraudulent:
            decision = "rejected"
            confidence = 0.5
            reasons["fraud"] = fraud_output
            
        # Policy checks return a dict. policy_output is Dict[str, bool] from evaluate.
        # e.g., {'within_limit': bool}
        if not policy_output.get("within_limit", True):
            decision = "rejected"
            confidence = 0.0
            reasons["policy"] = policy_output
            
        return {
            "audit_id": audit_id,
            "decision": decision,
            "reasons": reasons,
            "confidence": confidence,
            "trace": trace,
        }
