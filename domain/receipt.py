from typing import List, Optional
from pydantic import BaseModel, Field


class Receipt(BaseModel):
    """Domain model representing a parsed receipt.

    This class is frozen to enforce immutability.
    """

    raw_text: str
    ocr_confidence_score: float = 1.0
    readability_issues: List[str] = Field(default_factory=list)
    manipulated_receipt: bool = False
    merchant_name: str
    date: str
    amount: float
    currency: str = "USD"
    items: List[str] = Field(default_factory=list)

    class Config:
        frozen = True
