from typing import List
from pydantic import BaseModel, Field


class FraudResult(BaseModel):
    """Domain model representing the fraud risk score and indicators.

    This class is frozen to enforce immutability.
    """

    score: float = 0.0
    indicators: List[str] = Field(default_factory=list)
    explanation: str = ""

    class Config:
        frozen = True
