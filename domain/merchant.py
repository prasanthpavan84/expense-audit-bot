from pydantic import BaseModel, ConfigDict, Field


class Merchant(BaseModel):
    """Domain model representing a merchant.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    category: str | None = None
    is_restricted: bool = False
    aliases: list[str] = Field(default_factory=list)
