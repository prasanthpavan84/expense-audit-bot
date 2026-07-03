# core/agents/ocr_agent.py
"""Mock OCR Agent – extracts text from a receipt.

In a production system this would call an OCR library (e.g., Tesseract) or
Google Vision API. For the prototype we return a static dictionary.
"""

from __future__ import annotations

from core.agents.base_agent import BaseAgent, AgentResult, WorkflowContext


class OCRAgent(BaseAgent):
    """Extract raw text from a receipt image.

    The mock implementation pretends we have read an image and returns a
    simple string. It stores the result in the provided ``WorkflowContext``
    under the ``ocr`` key so downstream agents can access it.
    """

    def execute(self, ctx: WorkflowContext) -> AgentResult:
        # Mock OCR output
        ocr_output = {
            "text": "Date: 2023-05-01\nAmount: $123.45\nVendor: Acme Corp",
            "image_data": None,
        }
        ctx.set("ocr", ocr_output)
        return AgentResult(success=True, output=ocr_output, explanation="Mock OCR succeeded")
