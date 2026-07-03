from core.container.service_container import ServiceContainer
from core.validation.schemas import WorkflowContext, WorkflowResult, DecisionTrace
from app.agents.policy_agent import PolicyAgent
from domain.receipt import Receipt


class AnswerPolicyUseCase:
    """Orchestrates policy compliance evaluation on an expense/receipt."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        self.policy_agent = PolicyAgent(name="policy_agent", services=services)

    def execute(self, receipt: Receipt) -> WorkflowResult:
        context = WorkflowContext(input=receipt.raw_text, receipt=receipt)
        
        res = self.policy_agent.run(context)
        trace = DecisionTrace(
            agent_name=self.policy_agent.name,
            decision="POLICY_EVALUATED",
            confidence=res.confidence,
            reason=res.explanation
        )

        status = "COMPLETED" if res.status == "SUCCESS" else "FAILED"
        return WorkflowResult(
            status=status,
            output=res.output,
            trace=[trace]
        )
