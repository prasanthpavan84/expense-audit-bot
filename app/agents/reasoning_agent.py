from core.agents.base_agent import BaseAgent
from core.validation.schemas import AgentResult, WorkflowContext
from core.metadata.capability import capability
from app.services.reasoning_service import ReasoningService
from app.core.config_manager import config
from typing import Optional

@capability(
    name="reasoning_agent",
    version="1.0.0",
    inputs=["receipt", "policy_res"],
    outputs=["reasoning_res"]
)
class ReasoningAgent(BaseAgent):
    """Reasoning Agent performs financial calculations and currency conversions."""

    def __init__(self, reasoning_service: Optional[ReasoningService] = None, **kwargs):
        super().__init__(**kwargs)
        self.reasoning_service = reasoning_service or ReasoningService()

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.logger.info("Reasoning Agent performing calculations.")
        receipt = context.get("receipt")
        if not receipt:
            return AgentResult(
                status="FAILED",
                output=None,
                confidence=0.0,
                explanation="Reasoning failed: receipt is missing."
            )

        # Get values from metadata or context
        claimed = receipt.amount
        currency = receipt.currency
        reimbursable = context.metadata.get("reimbursable_amount", claimed)
        rejected = context.metadata.get("rejected_amount", 0.0)

        # 1. Verify arithmetic: claimed = reimbursable + rejected
        is_arithmetic_valid = self.reasoning_service.verify_arithmetic(claimed, reimbursable, rejected)
        if not is_arithmetic_valid:
            # Recompute to be safe
            reimbursable = claimed - rejected
            context.metadata["reimbursable_amount"] = reimbursable
            self.logger.warning("Reasoning Agent adjusted reimbursable amount to match claimed total.")

        # 2. Convert to USD value for reporting
        amount_usd = self.reasoning_service.convert_to_usd(claimed, currency)
        
        output = {
            "claimed_amount_usd": amount_usd,
            "reimbursable_amount": reimbursable,
            "rejected_amount": rejected,
            "arithmetic_valid": True
        }
        
        context.metadata["claimed_amount_usd"] = amount_usd

        return AgentResult(
            status="SUCCESS",
            output=output,
            confidence=1.0,
            explanation=f"Arithmetic verification completed. Claimed {currency} {claimed:.2f} (USD {amount_usd:.2f}) -> Reimbursable: {reimbursable:.2f}, Rejected: {rejected:.2f}."
        )
