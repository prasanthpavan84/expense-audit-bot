from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import WorkflowContext, AgentResult
from app.fraud_detector import calculate_fraud_score
from domain.fraud import FraudResult


@capability(
    name="fraud_agent",
    version="1.0.0",
    inputs=["receipt"],
    outputs=["fraud_res"]
)
class FraudAgent(BaseAgent):
    """Fraud detection agent that calculates fraud score and indicators."""

    def initialize(self) -> None:
        super().initialize()
        self.logger.info("Fraud agent initialized.")

    def execute(self, context: WorkflowContext) -> AgentResult:
        if not context.receipt:
            return AgentResult(
                status="FAILED",
                output=None,
                confidence=0.0,
                explanation="Fraud detection failed: receipt is missing."
            )

        exp_dict = context.receipt.model_dump()
        score, flags = calculate_fraud_score(exp_dict)

        if not flags or flags == "No suspicious anomalies detected.":
            indicators = []
        else:
            indicators = [f.strip() for f in flags.split(";") if f.strip()]

        score_normalized = score / 100.0

        fraud_res = FraudResult(
            score=score_normalized,
            indicators=indicators,
            explanation=f"Fraud score: {score_normalized:.2f}. Triggered flags: {', '.join(indicators) if indicators else 'none'}"
        )

        status = "SUCCESS" if score_normalized <= 0.7 else "FAILED"

        return AgentResult(
            status=status,
            output=fraud_res,
            confidence=1.0,
            explanation=fraud_res.explanation
        )
