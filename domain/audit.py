from typing import List
from pydantic import BaseModel, Field


class Audit(BaseModel):
    """Domain model representing the audit decision trace and final resolution.

    This class is frozen to enforce immutability.
    """

    expense_id: str
    is_approved: bool = False
    reason: str = ""
    decision_trace: List[str] = Field(default_factory=list)

    class Config:
        frozen = True
