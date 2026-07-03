from typing import List
from pydantic import BaseModel, Field

from .expense import Expense


class Report(BaseModel):
    """Domain model representing the compiled audit report.

    This class is frozen to enforce immutability.
    """

    id: str
    created_at: str
    expenses: List[Expense] = Field(default_factory=list)
    summary: str = ""
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, ESCALATED

    class Config:
        frozen = True
        arbitrary_types_allowed = True
