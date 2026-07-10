from app.services.receipt_service import ReceiptService
from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import AgentResult, WorkflowContext


@capability(name="receipt_extractor", version="1.0.0", inputs=["input"], outputs=["receipt"])
class ReceiptAgent(BaseAgent):
    """Receipt Agent extracts items and metadata using ReceiptService."""

    def __init__(self, receipt_service: ReceiptService | None = None, **kwargs):
        super().__init__(**kwargs)
        self.receipt_service = receipt_service or ReceiptService()

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.logger.info("Receipt Agent extracting fields.")
        raw_input = context.input

        try:
            receipt = self.receipt_service.extract_fields(raw_input)
            context.set("receipt", receipt)
            context.metadata["receipt_data"] = receipt.model_dump()

            return AgentResult(
                status="SUCCESS",
                output=receipt,
                confidence=receipt.ocr_confidence_score,
                explanation=f"Extracted receipt for merchant {receipt.merchant_name} with amount {receipt.amount}.",
            )
        except Exception as e:
            return AgentResult(
                status="FAILED", output=None, confidence=0.0, explanation=f"Receipt extraction failed: {e!s}"
            )
