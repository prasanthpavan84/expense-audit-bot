import json
import os
from typing import Dict, Any, List, Tuple

def load_company_policy() -> Dict[str, Any]:
    policy_path = os.path.join(os.path.dirname(__file__), "company_policy.json")
    if os.path.exists(policy_path):
        try:
            with open(policy_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback default values
    return {
        "category_limits": {
            "Meals": {"limit": 50.0, "currency": "USD"},
            "Hotel": {"limit": 150.0, "currency": "USD"},
            "Travel": {"limit": 300.0, "currency": "USD"},
            "Software": {"limit": 100.0, "currency": "USD"},
            "Taxi": {"limit": 50.0, "currency": "USD"},
            "Flight": {"limit": 500.0, "currency": "USD"},
            "Other": {"limit": 25.0, "currency": "USD"}
        },
        "inr_limits": {
            "Meals": 3000.0,
            "Hotel": 12000.0,
            "Travel": 24000.0,
            "Software": 6000.0,
            "Taxi": 3000.0,
            "Flight": 40000.0,
            "Other": 1500.0
        },
        "role_multipliers": {
            "Intern": 0.5,
            "Associate": 1.0,
            "Manager": 1.5,
            "Executive": 3.0
        },
        "restricted_vendors": ["casino", "gambling", "club", "bar", "liquor", "pub", "lounge"],
        "exchange_rates": {
            "EUR": 1.10,
            "GBP": 1.30,
            "INR": 0.012,
            "CAD": 0.74,
            "AUD": 0.66,
            "JPY": 0.0065,
            "USD": 1.0
        }
    }

def evaluate_policy(
    expense: Dict[str, Any], 
    role: str = "Associate", 
    justification: str = None
) -> Tuple[float, float, float, List[str], str]:
    """
    Evaluates an expense against corporate policies deterministically.
    
    Returns:
        Tuple: (allowed_amount, reimbursable_amount, rejected_amount, violations, notes)
    """
    policy = load_company_policy()
    
    merchant = expense.get("merchant", "Unknown")
    category = expense.get("category", "Other")
    claimed_amount = float(expense.get("amount", 0.0))
    currency = expense.get("currency", "USD").upper()
    
    violations = []
    notes = []
    
    # 1. Vendor Restrictions Check
    is_restricted = False
    restricted_keywords = policy.get("restricted_vendors", [])
    for kw in restricted_keywords:
        if kw in merchant.lower():
            is_restricted = True
            violations.append(f"Restricted Vendor: '{merchant}' contains prohibited term '{kw}'.")
            break
            
    # Apply role multiplier
    role_multipliers = policy.get("role_multipliers", {})
    multiplier = role_multipliers.get(role.capitalize(), 1.0)
    if multiplier != 1.0:
        notes.append(f"Applied role multiplier {multiplier} for role '{role}'.")
        
    # Get rates
    rates = policy.get("exchange_rates", {})
    conversion_rate = rates.get(currency, 1.0)
    
    # 2. Spend Limit Calculations
    category_limits = policy.get("category_limits", {})
    inr_limits = policy.get("inr_limits", {})
    
    # Canonicalize category name
    cat_clean = category.capitalize()
    if cat_clean not in category_limits:
        # Check subcategories
        if "meal" in category.lower() or "food" in category.lower() or "pizza" in category.lower():
            cat_clean = "Meals"
        elif "hotel" in category.lower() or "stay" in category.lower() or "accommodation" in category.lower():
            cat_clean = "Hotel"
        elif "software" in category.lower() or "license" in category.lower():
            cat_clean = "Software"
        elif "flight" in category.lower():
            cat_clean = "Flight"
        elif "taxi" in category.lower() or "ride" in category.lower() or "cab" in category.lower():
            cat_clean = "Taxi"
        else:
            cat_clean = "Other"

    # Fetch baseline limit
    limit_amount = 25.0  # fallback
    limit_currency = "USD"
    
    # For INR directly, we have exact local currency limits in our config
    if currency == "INR" and cat_clean in inr_limits:
        limit_amount = inr_limits[cat_clean]
        limit_currency = "INR"
        notes.append(f"Using direct INR limit for {cat_clean}: INR {limit_amount:.2f}")
    elif cat_clean in category_limits:
        limit_amount = category_limits[cat_clean]["limit"]
        limit_currency = category_limits[cat_clean]["currency"]
        
    # Standard baseline limit (in transaction currency)
    if limit_currency != currency:
        # Convert category limit to target currency if we need to check limits
        # e.g., category limit is in USD, transaction is in EUR
        # category_limit_in_target = category_limit_usd / exchange_rate_target
        target_rate = rates.get(currency, 1.0)
        if target_rate > 0:
            limit_amount = limit_amount / target_rate
            notes.append(f"Converted USD limit to {currency} using rate {target_rate}")
            
    # Apply role multiplier to limit
    adjusted_limit = limit_amount * multiplier
    
    # Apply exception adjustments
    exception_applied = False
    if justification:
        justification_lower = justification.lower()
        if "executive" in justification_lower or "ceo" in justification_lower or "vp" in justification_lower or "boss" in justification_lower or "manager approved" in justification_lower:
            adjusted_limit = 999999999.0
            exception_applied = True
            notes.append("Rigorous limits bypassed under Executive Approval exception.")
        elif any(phrase in justification_lower for phrase in ["conference", "seminar", "summit", "workshop", "emergency", "crisis", "medical"]):
            adjusted_limit = adjusted_limit * 2.0
            exception_applied = True
            notes.append("Limits doubled under approved exception justification.")
            
    # Reimbursable vs. Rejected calculations
    allowed_amount = adjusted_limit
    
    if is_restricted:
        if justification and any(kw in justification.lower() for kw in ["executive", "ceo", "vp", "boss"]):
            reimbursable_amount = claimed_amount
            # Ensure the violation is cleared/removed since it is approved
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
