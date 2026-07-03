from typing import Dict, Any
from core.container.service_container import ServiceContainer
from core.validation.schemas import WorkflowContext, WorkflowResult, DecisionTrace
from app.agents.extraction_agent import ExtractionAgent
from app.agents.validation_agent import ValidationAgent


class ValidateReceiptUseCase:
    """Orchestrates receipt extraction and validation."""

    def __init__(self, services: ServiceContainer):
        self.services = services
        self.extractor = ExtractionAgent(name="receipt_extractor", services=services)
        self.validator = ValidationAgent(name="validation_agent", services=services)

    def execute(self, raw_input: str) -> WorkflowResult:
        context = WorkflowContext(input=raw_input)

        # 1. Extract receipt fields
        extraction_res = self.extractor.run(context)
        if extraction_res.status == "FAILED":
            trace = DecisionTrace(
                agent_name=self.extractor.name,
                decision="EXTRACTION_FAILED",
                confidence=extraction_res.confidence,
                reason=extraction_res.explanation
            )
            return WorkflowResult(
                status="FAILED",
                output=extraction_res.explanation,
                trace=[trace]
            )

        context.receipt = extraction_res.output
        trace_extract = DecisionTrace(
            agent_name=self.extractor.name,
            decision="EXTRACTION_SUCCESS",
            confidence=extraction_res.confidence,
            reason=extraction_res.explanation
        )

        # 2. Validate receipt fields
        validation_res = self.validator.run(context)
        trace_validate = DecisionTrace(
            agent_name=self.validator.name,
            decision="VALIDATION_FAILED" if validation_res.status == "FAILED" else "VALIDATION_SUCCESS",
            confidence=validation_res.confidence,
            reason=validation_res.explanation
        )

        if validation_res.status == "FAILED":
            context.metadata["validation_errors"] = validation_res.output
            return WorkflowResult(
                status="FAILED",
                output=validation_res.output,
                trace=[trace_extract, trace_validate]
            )

        return WorkflowResult(
            status="COMPLETED",
            output=context.receipt,
            trace=[trace_extract, trace_validate]
        )
