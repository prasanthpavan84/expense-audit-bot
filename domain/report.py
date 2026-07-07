from pydantic import BaseModel, ConfigDict, Field

from .expense import Expense


class Report(BaseModel):
    """Domain model representing the compiled audit report.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    created_at: str
    expenses: list[Expense] = Field(default_factory=list)
    summary: str = ""
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, ESCALATED
