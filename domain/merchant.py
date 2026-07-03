from typing import List, Optional
from pydantic import BaseModel, Field


class Merchant(BaseModel):
    """Domain model representing a merchant.

    This class is frozen to enforce immutability.
    """

    name: str
    category: Optional[str] = None
    is_restricted: bool = False
    aliases: List[str] = Field(default_factory=list)

    class Config:
        frozen = True
