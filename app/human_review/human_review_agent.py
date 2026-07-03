from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import WorkflowContext, AgentResult
from .review_queue import ReviewQueue


@capability(
    name="human_review_agent",
    version="1.0.0",
    inputs=["receipt", "fraud_res"],
    outputs=["review_status"]
)
class HumanReviewAgent(BaseAgent):
    """Agent representing the human review gate for high-risk expenses."""

    def initialize(self) -> None:
        super().initialize()
        self.queue = ReviewQueue()
        self.logger.info("Human Review agent initialized.")

    def execute(self, context: WorkflowContext) -> AgentResult:
        fraud_score = 0.0
        if context.fraud_res:
            fraud_score = context.fraud_res.score

        # Push to the human review queue if fraud risk or policy violations require it
        needs_review = fraud_score > 0.7 or (context.policy_res and not context.policy_res.is_compliant)
        
        if needs_review:
            import uuid
            item_id = str(uuid.uuid4())
            self.queue.push(item_id, context.input, fraud_score)
            
            # Emit HighRiskDetectedEvent via EventBus
            self.services.event_bus.publish(
                "HighRiskDetectedEvent",
                {"item_id": item_id, "input": context.input, "fraud_score": fraud_score}
            )
            
            return AgentResult(
                status="ESCALATED",
                output={"item_id": item_id, "status": "PENDING_REVIEW"},
                confidence=1.0,
                explanation="Expense escalated to human review due to high risk/violations."
            )

        return AgentResult(
            status="SUCCESS",
            output={"status": "APPROVED"},
            confidence=1.0,
            explanation="No human review required."
        )
