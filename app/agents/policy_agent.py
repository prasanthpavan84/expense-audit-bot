from app.core.config_manager import config
from app.services.policy_service import PolicyService
from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import AgentResult, WorkflowContext
from domain.policy import PolicyResult


@capability(name="policy_agent", version="1.0.0", inputs=["receipt"], outputs=["policy_res"])
class PolicyAgent(BaseAgent):
    """Policy Agent evaluates receipts against corporate policy using PolicyService."""

    def __init__(self, policy_service: PolicyService | None = None, **kwargs):
        super().__init__(**kwargs)
        self.policy_service = policy_service or PolicyService()

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.logger.info("Policy Agent evaluating policy.")
        receipt = context.get("receipt")
        if not receipt:
            return AgentResult(
                status="FAILED", output=None, confidence=0.0, explanation="Policy check failed: receipt is missing."
            )

        receipt_dict = receipt.model_dump()
        role = context.metadata.get("user_role", "Associate")
        justification = context.metadata.get("justification")

        # Load prompt version
        version = config.prompt_versions.get("policy_agent", "v1")

        try:
            allowed, reimbursable, rejected, violations, notes_str = self.policy_service.evaluate(
                receipt_dict, role, justification, policy_version=version
            )

            # Save results to context metadata
            context.metadata["policy_checks"] = dict.fromkeys(violations, True)
            context.metadata["policy_violations"] = violations
            context.metadata["allowed_amount"] = allowed
            context.metadata["reimbursable_amount"] = reimbursable
            context.metadata["rejected_amount"] = rejected

            # Format output
            status = "SUCCESS" if not violations else "FAILED"
            explanation = (
                "Policy compliance passed." if not violations else f"Policy violations: {'; '.join(violations)}"
            )

            notes_list = [notes_str] if isinstance(notes_str, str) else notes_str

            policy_result_obj = PolicyResult(
                violations=violations,
                allowed_amount=allowed,
                reimbursable_amount=reimbursable,
                rejected_amount=rejected,
                notes=notes_list,
            )

            return AgentResult(status=status, output=policy_result_obj, confidence=1.0, explanation=explanation)
        except Exception as e:
            return AgentResult(status="FAILED", output=None, confidence=0.0, explanation=f"Policy check failed: {e!s}")
