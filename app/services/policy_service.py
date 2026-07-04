import json
import os
from typing import Dict, Any, List, Tuple, Optional
from app.services.base_service import BaseService
from app.repositories.policy_repository import PolicyRepository
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.models.domain import Policy

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
        """Evaluates compliance using versioned policy configs."""
        
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

        # 1. Restricted Vendor Check
        is_restricted = False
        restricted_keywords = policy_data.get("restricted_vendors", [])
        for kw in restricted_keywords:
            if kw in merchant.lower():
                is_restricted = True
                violations.append(f"Restricted Vendor: '{merchant}' contains prohibited term '{kw}'.")
                break

        # 2. Role Multiplier
        role_multipliers = policy_data.get("role_multipliers", {})
        multiplier = role_multipliers.get(role.capitalize(), 1.0)
        if multiplier != 1.0:
            notes.append(f"Applied role multiplier {multiplier} for role '{role}'.")

        # 3. Currency conversion
        rates = policy_data.get("exchange_rates", {})
        
        # 4. Limit calculations
        category_limits = policy_data.get("category_limits", {})
        inr_limits = policy_data.get("inr_limits", {})

        cat_clean = category.capitalize()
        # Canonicalize category
        if cat_clean not in category_limits:
            if "meal" in category.lower() or "food" in category.lower() or "starbucks" in merchant.lower():
                cat_clean = "Meals"
            elif "hotel" in category.lower() or "stay" in category.lower():
                cat_clean = "Hotel"
            elif "software" in category.lower() or "license" in category.lower():
                cat_clean = "Software"
            elif "flight" in category.lower():
                cat_clean = "Flight"
            elif "taxi" in category.lower() or "ride" in category.lower() or "cab" in category.lower():
                cat_clean = "Taxi"
            else:
                cat_clean = "Other"

        limit_amount = 25.0
        limit_currency = "USD"

        if currency == "INR" and cat_clean in inr_limits:
            limit_amount = inr_limits[cat_clean]
            limit_currency = "INR"
            notes.append(f"Using direct INR limit for {cat_clean}: INR {limit_amount:.2f}")
        elif cat_clean in category_limits:
            limit_amount = category_limits[cat_clean]["limit"]
            limit_currency = category_limits[cat_clean]["currency"]

        if limit_currency != currency:
            target_rate = rates.get(currency, 1.0)
            if target_rate > 0:
                limit_amount = limit_amount / target_rate
                notes.append(f"Converted USD limit to {currency} using rate {target_rate}")

        adjusted_limit = limit_amount * multiplier

        # Justification exceptions
        if justification:
            justification_lower = justification.lower()
            if "executive" in justification_lower or "ceo" in justification_lower or "vp" in justification_lower or "boss" in justification_lower or "manager approved" in justification_lower:
                adjusted_limit = 999999999.0
                notes.append("Rigorous limits bypassed under Executive Approval exception.")
            elif any(phrase in justification_lower for phrase in ["conference", "seminar", "summit", "workshop", "emergency", "crisis", "medical"]):
                adjusted_limit = adjusted_limit * 2.0
                notes.append("Limits doubled under approved exception justification.")

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
                notes.append(f"Claim exceeded spending limit by {currency} {claimed_amount - adjusted_limit:,.2f}.")

        rejected_amount = claimed_amount - reimbursable_amount
        notes_str = " ".join(notes) if notes else "No policy deviations found."
        
        return allowed_amount, reimbursable_amount, rejected_amount, violations, notes_str
