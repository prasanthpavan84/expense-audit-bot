from pydantic import BaseModel, ConfigDict, Field

from .fraud import FraudResult
from .policy import PolicyResult


class Expense(BaseModel):
    """Domain model representing an expense item.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    employee_id: str
    merchant: str
    date: str
    amount: float
    currency: str = "USD"
    category: str = "Other"
    items: list[str] = Field(default_factory=list)
    justification: str | None = None
    policy_result: PolicyResult | None = None
    fraud_result: FraudResult | None = None
