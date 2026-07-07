from pydantic import BaseModel, ConfigDict, Field


class Audit(BaseModel):
    """Domain model representing the audit decision trace and final resolution.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True)

    expense_id: str
    is_approved: bool = False
    reason: str = ""
    decision_trace: list[str] = Field(default_factory=list)
