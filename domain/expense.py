from typing import List, Optional
from pydantic import BaseModel, Field

from .policy import PolicyResult
from .fraud import FraudResult


class Expense(BaseModel):
    """Domain model representing an expense item.

    This class is frozen to enforce immutability.
    """

    id: str
    employee_id: str
    merchant: str
    date: str
    amount: float
    currency: str = "USD"
    category: str = "Other"
    items: List[str] = Field(default_factory=list)
    justification: Optional[str] = None
    policy_result: Optional[PolicyResult] = None
    fraud_result: Optional[FraudResult] = None

    class Config:
        frozen = True
        arbitrary_types_allowed = True
