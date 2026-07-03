from typing import List
from pydantic import BaseModel, Field


class PolicyResult(BaseModel):
    """Domain model representing the result of evaluating an expense against policies.

    This class is frozen to enforce immutability.
    """

    violations: List[str] = Field(default_factory=list)
    allowed_amount: float = 0.0
    reimbursable_amount: float = 0.0
    rejected_amount: float = 0.0
    notes: List[str] = Field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return len(self.violations) == 0

    class Config:
        frozen = True
