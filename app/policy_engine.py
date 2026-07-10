from typing import Any

from app.repositories.policy_repository import PolicyRepository
from app.services.policy_service import PolicyService


def load_company_policy() -> dict[str, Any]:
    return PolicyRepository().get_policy_by_version("v1")


def evaluate_policy(
    expense: dict[str, Any], role: str = "Associate", justification: str = None, session_id: str = None
) -> tuple[float, float, float, list[str], str]:
    """Backward compatibility wrapper mapping to PolicyService."""
    service = PolicyService()
    return service.evaluate(expense, role, justification)
