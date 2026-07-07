from pydantic import BaseModel, ConfigDict


class Employee(BaseModel):
    """Domain model representing an employee.

    This class is frozen to enforce immutability.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    role: str = "Associate"
    department: str = "Engineering"
