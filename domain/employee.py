from pydantic import BaseModel


class Employee(BaseModel):
    """Domain model representing an employee.

    This class is frozen to enforce immutability.
    """

    id: str
    name: str
    role: str = "Associate"
    department: str = "Engineering"

    class Config:
        frozen = True
