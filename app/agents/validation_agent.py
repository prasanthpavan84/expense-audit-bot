from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import WorkflowContext, AgentResult
from app.validation import validate_expenses


@capability(
    name="validation_agent",
    version="1.0.0",
    inputs=["input", "receipt"],
    outputs=["validation_errors"]
)
class ValidationAgent(BaseAgent):
    """Validation agent that validates the receipt data against schemas and rules."""

    def initialize(self) -> None:
        super().initialize()
        self.logger.info("Validation agent initialized.")

    def execute(self, context: WorkflowContext) -> AgentResult:
        if not context.receipt:
            return AgentResult(
                status="FAILED",
                output=["No receipt data found in context."],
                confidence=0.0,
                explanation="Validation failed: receipt is missing."
            )

        # Map receipt domain model back to format expected by validate_expenses
        receipt_dict = context.receipt.model_dump()
        errors = validate_expenses([receipt_dict], context.input)
        
        if errors:
            return AgentResult(
                status="FAILED",
                output=errors,
                confidence=1.0,
                explanation="Validation errors: " + "; ".join(errors)
            )

        return AgentResult(
            status="SUCCESS",
            output=[],
            confidence=1.0,
            explanation="All validation checks passed."
        )

    def post_execute(self, result: AgentResult) -> None:
        super().post_execute(result)
        # We can store validation errors or status back into context
        if hasattr(self, "services") and self.services and hasattr(self.services, "memory") and self.services.memory:
            self.services.memory.receipt.add(result)
