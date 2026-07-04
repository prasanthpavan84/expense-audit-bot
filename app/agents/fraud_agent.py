from core.agents.base_agent import BaseAgent
from core.validation.schemas import AgentResult, WorkflowContext
from core.metadata.capability import capability
from app.services.fraud_service import FraudService
from app.models.domain import FraudSignal
from app.repositories.audit_repository import AuditRepository
from app.core.config_manager import config
from typing import Optional

@capability(
    name="fraud_agent",
    version="1.0.0",
    inputs=["receipt"],
    outputs=["fraud_res"]
)
class FraudAgent(BaseAgent):
    """Fraud Agent assesses risk and indicators utilizing FraudService."""

    def __init__(self, fraud_service: Optional[FraudService] = None, audit_repository: Optional[AuditRepository] = None, **kwargs):
        super().__init__(**kwargs)
        self.fraud_service = fraud_service or FraudService()
        self.audit_repository = audit_repository or AuditRepository()

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.logger.info("Fraud Agent performing risk checks.")
        receipt = context.get("receipt")
        if not receipt:
            return AgentResult(
                status="FAILED",
                output=None,
                confidence=0.0,
                explanation="Fraud check failed: receipt is missing."
            )

        # Retrieve history from database for duplicate checking
        history_expenses = self.audit_repository.find_all()
        # Map to dict format expected by fraud_service
        history_dicts = []
        for exp in history_expenses:
            history_dicts.append({
                "merchant": exp.merchant,
                "amount": exp.amount,
                "date": exp.date,
                "currency": exp.currency
            })

        receipt_dict = receipt.model_dump()
        
        try:
            fraud_signal = self.fraud_service.verify_fraud(receipt_dict, history_dicts)
            context.set("fraud_res", fraud_signal)
            context.metadata["fraud_indicators"] = fraud_signal.indicators
            context.metadata["fraud_score"] = int(fraud_signal.score * 100)
            
            status_str = "SUCCESS" if fraud_signal.score <= 0.7 else "FAILED"
            
            return AgentResult(
                status=status_str,
                output=fraud_signal,
                confidence=1.0 - fraud_signal.score,
                explanation=fraud_signal.explanation
            )
        except Exception as e:
            return AgentResult(
                status="FAILED",
                output=None,
                confidence=0.0,
                explanation=f"Fraud check failed: {str(e)}"
            )
