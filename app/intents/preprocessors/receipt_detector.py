"""Receipt Detector — independent from intent classification.

Scores receipt probability based on financial and structural indicators
(merchant, currency, tax, subtotal, invoice, date, payment method, etc.).
This runs *before* intent detection to provide a strong signal.
Zero LLM calls.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiptDetectionResult:
    """Immutable receipt detection result."""

    is_receipt: bool
    probability: float
    matched_indicators: tuple  # frozen tuple of matched indicator names
    reason: str


# Each indicator has a name, a regex pattern, and a weight
_RECEIPT_INDICATORS: list[dict] = [
    {"name": "currency_symbol", "pattern": re.compile(r"[\$\u20b9\u00a3\u20ac\u00a5]"), "weight": 0.12},
    {"name": "total_keyword", "pattern": re.compile(r"\btotal\b", re.I), "weight": 0.15},
    {"name": "subtotal_keyword", "pattern": re.compile(r"\bsub\s*total\b", re.I), "weight": 0.12},
    {"name": "tax_keyword", "pattern": re.compile(r"\btax\b", re.I), "weight": 0.10},
    {"name": "gst_vat_keyword", "pattern": re.compile(r"\b(gst|vat|cgst|sgst|igst)\b", re.I), "weight": 0.10},
    {"name": "invoice_keyword", "pattern": re.compile(r"\binvoice\b", re.I), "weight": 0.10},
    {"name": "receipt_keyword", "pattern": re.compile(r"\breceipt\b", re.I), "weight": 0.12},
    {"name": "receipt_number", "pattern": re.compile(r"\breceipt\s*#?\s*\d+", re.I), "weight": 0.10},
    {
        "name": "payment_method",
        "pattern": re.compile(r"\b(visa|mastercard|amex|debit|credit|cash|card|upi|paypal)\b", re.I),
        "weight": 0.08,
    },
    {"name": "date_pattern", "pattern": re.compile(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}"), "weight": 0.06},
    {"name": "time_pattern", "pattern": re.compile(r"\d{1,2}:\d{2}(:\d{2})?(\s*(am|pm))?", re.I), "weight": 0.04},
    {"name": "monetary_amount", "pattern": re.compile(r"\d+[.,]\d{2}\b"), "weight": 0.10},
    {"name": "change_due", "pattern": re.compile(r"\bchange\s*(due)?\b", re.I), "weight": 0.08},
    {"name": "merchant_header", "pattern": re.compile(r"^[A-Z][A-Za-z\s&'.-]{2,30}$", re.M), "weight": 0.05},
]

# Threshold above which we consider the input a receipt
_RECEIPT_THRESHOLD = 0.35


class ReceiptDetector:
    """Deterministic receipt detector — no LLM calls."""

    @staticmethod
    def detect(text: str) -> ReceiptDetectionResult:
        """Score receipt probability from structural/financial indicators."""
        if not text or not text.strip():
            return ReceiptDetectionResult(False, 0.0, (), "Empty input")

        matched: list[str] = []
        score = 0.0

        for indicator in _RECEIPT_INDICATORS:
            if indicator["pattern"].search(text):
                matched.append(indicator["name"])
                score += indicator["weight"]

        # Cap at 1.0
        score = min(score, 1.0)
        is_receipt = score >= _RECEIPT_THRESHOLD

        reason = (
            f"Receipt score {score:.2f} from {len(matched)} indicators" if matched else "No receipt indicators found"
        )

        return ReceiptDetectionResult(
            is_receipt=is_receipt,
            probability=round(score, 3),
            matched_indicators=tuple(matched),
            reason=reason,
        )
