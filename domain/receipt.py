from pydantic import BaseModel, ConfigDict, Field


class Receipt(BaseModel):
    """Domain model representing a parsed receipt.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True)

    raw_text: str
    ocr_confidence_score: float = 1.0
    readability_issues: list[str] = Field(default_factory=list)
    manipulated_receipt: bool = False
    merchant_name: str
    date: str
    amount: float
    currency: str = "USD"
    items: list[str] = Field(default_factory=list)
    category: str = "Other"
