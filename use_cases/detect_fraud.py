from core.container.service_container import ServiceContainer
from core.validation.schemas import WorkflowContext, WorkflowResult, DecisionTrace
from app.agents.fraud_agent import FraudAgent
from domain.receipt import Receipt


class DetectFraudUseCase:
    """Orchestrates fraud risk assessment on an expense/receipt."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        self.fraud_agent = FraudAgent(name="fraud_agent", services=services)

    def execute(self, receipt: Receipt) -> WorkflowResult:
        context = WorkflowContext(input=receipt.raw_text, receipt=receipt)
        
        res = self.fraud_agent.run(context)
        trace = DecisionTrace(
            agent_name=self.fraud_agent.name,
            decision="FRAUD_EVALUATED",
            confidence=res.confidence,
            reason=res.explanation
        )

        status = "COMPLETED" if res.status == "SUCCESS" else "FAILED"
        return WorkflowResult(
            status=status,
            output=res.output,
            trace=[trace]
        )
