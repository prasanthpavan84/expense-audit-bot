import json
import os
from typing import Dict, Any, List, Tuple, Optional
from app.services.base_service import BaseService
from app.repositories.policy_repository import PolicyRepository
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.models.domain import Policy
from app.utils.finance import safe_round, safe_add, safe_sub, convert_currency

class PolicyService(BaseService):
    """Business service evaluating policy compliance using versioned policies and RAG context."""

    def __init__(self, policy_repository: Optional[PolicyRepository] = None, knowledge_retrieval_service: Optional[KnowledgeRetrievalService] = None):
        self.policy_repository = policy_repository or PolicyRepository()
        self.knowledge_retrieval_service = knowledge_retrieval_service or KnowledgeRetrievalService()

    def evaluate(
        self,
        expense: Dict[str, Any],
        role: str = "Associate",
        justification: str = None,
        policy_version: str = "v1"
    ) -> Tuple[float, float, float, List[str], str]:
        """Evaluates compliance using versioned policy configs, employee country/grade, and citations."""
        
        # Load active policy (either by version or dynamically by date)
        date_str = expense.get("date", "Unknown")
        if policy_version == "v1" and date_str and date_str != "Unknown":
            # Retrieve active policy version dynamically
            policy_data = self.policy_repository.get_policy_by_date(date_str)
        else:
            policy_data = self.policy_repository.get_policy_by_version(policy_version)

        merchant = expense.get("merchant", "Unknown")
        category = expense.get("category", "Other")
        claimed_amount = float(expense.get("amount", 0.0))
        currency = expense.get("currency", "USD").upper()

        violations = []
        notes = []

        # Resolve employee details: country/grade/role
        EMPLOYEE_REGISTRY = {
            "EMP102": {"name": "John Doe", "department": "Engineering", "role": "Associate", "country": "USA", "grade": "Level 2"},
            "EMP103": {"name": "Jane Smith", "department": "Marketing", "role": "Manager", "country": "India", "grade": "Level 3"},
            "EMP104": {"name": "Alice Johnson", "department": "Sales", "role": "Executive", "country": "UK", "grade": "Level 4"},
            "EMP105": {"name": "Bob Brown", "department": "Operations", "role": "Intern", "country": "Canada", "grade": "Level 1"},
        }
        
        employee_info = EMPLOYEE_REGISTRY.get(role, None)
        if employee_info:
            actual_role = employee_info["role"]
            actual_grade = employee_info["grade"]
            actual_country = employee_info["country"]
        else:
            # Fallback if raw role string passed
            cap_role = role.capitalize()
            valid_roles = ["Intern", "Associate", "Manager", "Executive"]
            actual_role = cap_role if cap_role in valid_roles else "Associate"
            actual_grade = "Level 2" if actual_role == "Associate" else "Level 1" if actual_role == "Intern" else "Level 3" if actual_role == "Manager" else "Level 4"
            actual_country = "India" if currency == "INR" else "USA"

        # 1. Restricted Vendor Check
        is_restricted = False
        restricted_keywords = policy_data.get("restricted_vendors", [])
        for kw in restricted_keywords:
            if kw in merchant.lower():
                is_restricted = True
                violations.append(f"Restricted Vendor: '{merchant}' contains prohibited term '{kw}'.")
                notes.append(f"Citation: [Company Policy Section 3.1: Prohibited restricted vendor '{merchant}'].")
                break

        # 2. Role Multiplier
        role_multipliers = policy_data.get("role_multipliers", {})
        multiplier = role_multipliers.get(actual_role.capitalize(), 1.0)
        if multiplier != 1.0:
            notes.append(f"Citation: [Company Policy Section 4.3: Applied Grade Multiplier of {multiplier}x for {actual_role} ({actual_grade})].")

        # 3. Currency conversion
        rates = policy_data.get("exchange_rates", {})
        
        # 4. Limit calculations
        category_limits = policy_data.get("category_limits", {})
        inr_limits = policy_data.get("inr_limits", {})

        cat_clean = category.capitalize()
        # Canonicalize category
        if cat_clean not in category_limits:
            if "meal" in category.lower() or "food" in category.lower() or "starbucks" in merchant.lower() or "subway" in merchant.lower():
                cat_clean = "Meals"
            elif "hotel" in category.lower() or "stay" in category.lower() or "hilton" in merchant.lower():
                cat_clean = "Hotel"
            elif "software" in category.lower() or "license" in category.lower():
                cat_clean = "Software"
            elif "flight" in category.lower():
                cat_clean = "Flight"
            elif "taxi" in category.lower() or "ride" in category.lower() or "cab" in category.lower() or "uber" in merchant.lower():
                cat_clean = "Taxi"
            else:
                cat_clean = "Other"

        limit_amount = 25.0
        limit_currency = "USD"

        # Enforce country hierarchy limits
        if actual_country == "India" or currency == "INR":
            if cat_clean in inr_limits:
                limit_amount = inr_limits[cat_clean]
                limit_currency = "INR"
                notes.append(f"Citation: [Company Policy Section 4.2: Category {cat_clean} limit for India is INR {limit_amount:.2f}].")
        elif cat_clean in category_limits:
            limit_amount = category_limits[cat_clean]["limit"]
            limit_currency = category_limits[cat_clean]["currency"]
            notes.append(f"Citation: [Company Policy Section 4.2: Category {cat_clean} limit is {limit_currency} {limit_amount:.2f}].")

        if limit_currency != currency:
            limit_amount = convert_currency(limit_amount, limit_currency, currency, rates)
            notes.append(f"Converted {limit_currency} limit to {currency} via USD base rate")

        adjusted_limit = safe_round(limit_amount * multiplier)

        # Justification exceptions
        if justification:
            justification_lower = justification.lower()
            if "executive" in justification_lower or "ceo" in justification_lower or "vp" in justification_lower or "boss" in justification_lower or "manager approved" in justification_lower:
                adjusted_limit = 999999999.0
                notes.append("Citation: [Company Policy Section 5.1: Rigorous limits bypassed under Executive Approval exception].")
            elif any(phrase in justification_lower for phrase in ["conference", "seminar", "summit", "workshop", "emergency", "crisis", "medical"]):
                adjusted_limit = safe_round(adjusted_limit * 2.0)
                notes.append("Citation: [Company Policy Section 5.2: Limits doubled under approved exception justification].")

        allowed_amount = adjusted_limit

        if is_restricted:
            if justification and any(kw in justification.lower() for kw in ["executive", "ceo", "vp", "boss"]):
                reimbursable_amount = claimed_amount
                violations = []
                notes.append("Restricted vendor purchase approved via Executive exception.")
            else:
                reimbursable_amount = 0.0
                notes.append("Transaction at restricted vendor is prohibited and rejected.")
        else:
            reimbursable_amount = min(claimed_amount, adjusted_limit)
            if claimed_amount > adjusted_limit:
                violation_msg = f"{cat_clean} limit exceeded. Limit is {currency} {adjusted_limit:,.2f}, Claimed {currency} {claimed_amount:,.2f}"
                violations.append(violation_msg)
                notes.append(f"Claim exceeded spending limit by {currency} {safe_sub(claimed_amount, adjusted_limit):,.2f}.")

        rejected_amount = safe_sub(claimed_amount, reimbursable_amount)
        notes_str = " ".join(notes) if notes else "No policy deviations found."
        
        return allowed_amount, reimbursable_amount, rejected_amount, violations, notes_str
