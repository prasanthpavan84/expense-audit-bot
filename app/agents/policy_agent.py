from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import WorkflowContext, AgentResult
from app.policy_engine import evaluate_policy
from domain.policy import PolicyResult


@capability(
    name="policy_agent",
    version="1.0.0",
    inputs=["receipt"],
    outputs=["policy_res"]
)
class PolicyAgent(BaseAgent):
    """Policy evaluation agent that assesses an expense against corporate rules."""

    def initialize(self) -> None:
        super().initialize()
        self.logger.info("Policy agent initialized.")

    def execute(self, context: WorkflowContext) -> AgentResult:
        if not context.receipt:
            return AgentResult(
                status="FAILED",
                output=None,
                confidence=0.0,
                explanation="Policy evaluation failed: receipt is missing."
            )

        receipt_dict = context.receipt.model_dump()
        allowed, reimbursable, rejected, violations, notes_str = evaluate_policy(receipt_dict)

        if not notes_str or notes_str == "No policy deviations found.":
            notes_list = []
        else:
            # Split by '.' but keep the parts as strings. Filter out empty strings.
            notes_list = [n.strip() for n in notes_str.split(".") if n.strip()]

        policy_res = PolicyResult(
            violations=violations,
            allowed_amount=allowed,
            reimbursable_amount=reimbursable,
            rejected_amount=rejected,
            notes=notes_list
        )

        status = "SUCCESS" if policy_res.is_compliant else "FAILED"
        explanation = (
            "Policy evaluation passed."
            if policy_res.is_compliant
            else f"Policy violations: {'; '.join(violations)}"
        )

        return AgentResult(
            status=status,
            output=policy_res,
            confidence=1.0,
            explanation=explanation
        )
