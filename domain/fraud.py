from pydantic import BaseModel, ConfigDict, Field


class FraudResult(BaseModel):
    """Domain model representing the fraud risk score and indicators.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True)

    score: float = 0.0
    indicators: list[str] = Field(default_factory=list)
    explanation: str = ""
