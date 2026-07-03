from typing import List
from core.container.service_container import ServiceContainer
from core.validation.schemas import WorkflowContext, WorkflowResult, DecisionTrace
from app.agents.report_agent import ReportAgent
from .validate_receipt import ValidateReceiptUseCase
from .detect_fraud import DetectFraudUseCase
from .answer_policy import AnswerPolicyUseCase


class AuditExpenseUseCase:
    """Orchestrates the entire expense auditing workflow."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        self.validate_use_case = ValidateReceiptUseCase(services)
        self.fraud_use_case = DetectFraudUseCase(services)
        self.policy_use_case = AnswerPolicyUseCase(services)
        self.report_agent = ReportAgent(name="report_agent", services=services)

    def execute(self, raw_input: str) -> WorkflowResult:
        traces: List[DecisionTrace] = []
        context = WorkflowContext(input=raw_input)

        # 1. Extraction & Validation
        val_result = self.validate_use_case.execute(raw_input)
        traces.extend(val_result.trace)

        if val_result.status == "FAILED":
            # Set validation errors to be captured by report agent
            context.metadata["validation_errors"] = val_result.output
            
            # Generate failure/rejection report
            report_res = self.report_agent.run(context)
            trace_report = DecisionTrace(
                agent_name=self.report_agent.name,
                decision="REPORT_GENERATED",
                confidence=report_res.confidence,
                reason="Generated audit report for validation failure."
            )
            traces.append(trace_report)
            return WorkflowResult(
                status="FAILED",
                output=report_res.output,
                trace=traces
            )

        # Validation passed, extract receipt and run audit evaluations
        receipt = val_result.output
        context.receipt = receipt

        # 2. Fraud Check
        fraud_result = self.fraud_use_case.execute(receipt)
        traces.extend(fraud_result.trace)
        context.fraud_res = fraud_result.output

        # 3. Policy Compliance Check
        policy_result = self.policy_use_case.execute(receipt)
        traces.extend(policy_result.trace)
        context.policy_res = policy_result.output

        # 4. Report Generation
        report_res = self.report_agent.run(context)
        trace_report = DecisionTrace(
            agent_name=self.report_agent.name,
            decision="REPORT_GENERATED",
            confidence=report_res.confidence,
            reason="Generated final audit report."
        )
        traces.append(trace_report)

        status = "COMPLETED"
        if context.fraud_res and context.fraud_res.score > 0.7:
            status = "FAILED"
        elif context.policy_res and not context.policy_res.is_compliant:
            status = "FAILED"

        return WorkflowResult(
            status=status,
            output=report_res.output,
            trace=traces
        )
