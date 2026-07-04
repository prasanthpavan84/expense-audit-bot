from typing import Dict, Any, List, Tuple
from app.services.policy_service import PolicyService
from app.repositories.policy_repository import PolicyRepository

def load_company_policy() -> Dict[str, Any]:
    return PolicyRepository().get_policy_by_version("v1")

def evaluate_policy(
    expense: Dict[str, Any], 
    role: str = "Associate", 
    justification: str = None,
    session_id: str = None
) -> Tuple[float, float, float, List[str], str]:
    """Backward compatibility wrapper mapping to PolicyService."""
    service = PolicyService()
    return service.evaluate(expense, role, justification)
