import re
import datetime
import json
import os
from typing import List, Dict, Any, Optional

class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors

def load_policy_config() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "company_policy.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
      "category_limits": {"Meals": {"limit": 50.0}},
      "restricted_vendors": ["casino", "gambling", "club", "bar", "liquor", "pub", "lounge"]
    }

def validate_date(date_str: str) -> Optional[str]:
    """Validate format and that it is not in the future relative to 2026-06-30."""
    if not date_str or date_str.lower() in ["unknown", "none", "null"]:
        return None  # Missing date is escalated to HITL review, not a hard format error
    
    # Check format YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return f"Date '{date_str}' is not in YYYY-MM-DD format."
        
    try:
        year, month, day = map(int, date_str.split("-"))
        dt = datetime.date(year, month, day)
    except ValueError:
        return f"Date '{date_str}' is mathematically invalid."
        
    # Future date check
    today = datetime.date(2026, 6, 30)
    if dt > today:
        return f"Date '{date_str}' is in the future. Expense dates cannot be in the future."
        
    return None

def validate_currency(currency: str) -> Optional[str]:
    if not currency or currency.lower() in ["unknown", "none", "null"]:
        return None  # Missing currency is escalated to HITL review, not a hard error
    if not re.match(r"^[A-Z]{3}$", currency.upper()) and currency not in ["₹", "$", "€", "£"]:
        return f"Currency code '{currency}' must be a 3-letter code or valid symbol."
    return None

def check_hallucination(extracted: Dict[str, Any], raw_text: str) -> List[str]:
    """Verify that extracted values match or exist in the raw input text to detect LLM hallucinations."""
    if not raw_text:
        return []
        
    errors = []
    text_lower = raw_text.lower()
    
    # 1. Merchant Check
    merchant = extracted.get("merchant", "")
    if merchant and merchant.lower() != "unknown" and merchant.lower() != "other":
        # Remove punctuation for matching
        clean_text_for_merchant = re.sub(r"[^\w\s]", " ", text_lower)
        clean_merchant = re.sub(r"[^\w\s]", " ", merchant.lower())
        words = [w.strip() for w in re.split(r"\s+", clean_merchant) if len(w.strip()) > 1]
        is_exemption = (clean_merchant.strip() == "taxi ride" and any(kw in clean_text_for_merchant for kw in ["uber", "taxi", "cab", "ride"]))
        if not is_exemption and words and not any(word in clean_text_for_merchant for word in words):
            errors.append(f"Extracted merchant '{merchant}' was not found in the original text (possible hallucination).")
            
    # 2. Amount Check
    amount = extracted.get("amount", 0.0)
    if amount > 0:
        amt_str = f"{amount:.2f}"
        amt_str_short = f"{int(amount)}"
        clean_text = re.sub(r"[,\$\u20b9\u00a3\u20ac]", "", text_lower)
        if amt_str not in clean_text and amt_str_short not in clean_text:
            nums = re.findall(r"\d+", clean_text)
            if not any(int(n) == int(amount) for n in nums):
                errors.append(f"Extracted amount '{amount}' was not found in the original text (possible hallucination).")
                
    return errors

def validate_single_expense(expense: Dict[str, Any], raw_text: str, history: List[Dict[str, Any]] = None, session_id: str = None) -> List[str]:
    errors = []
    if session_id:
        print(f"AUDIT_TRACE: [Session: {session_id}] Validating expense: {expense.get('merchant')} - {expense.get('amount')}")
    
    # 1. Amounts Check (Hard Error)
    amount = expense.get("amount")
    if amount is not None:
        try:
            val = float(amount)
            if val < 0:
                errors.append(f"Invalid amount {amount}: Amounts must be positive (cannot be negative).")
            elif val == 0:
                errors.append(f"Invalid amount {amount}: Amount cannot be zero.")
            elif val > 1000000.0:
                errors.append(f"Invalid amount {amount}: Amount exceeds processing limit ($1,000,000).")
        except (ValueError, TypeError):
            errors.append(f"Invalid amount {amount}: Amount must be a valid number.")
    else:
        # Missing amount is a hard validation error because we cannot calculate anything without it
        errors.append("Amount is missing.")
            
    # 2. Dates Format Check (Hard Error only if provided and malformed)
    date_val = expense.get("date")
    if date_val:
        date_err = validate_date(str(date_val))
        if date_err:
            errors.append(date_err)
            
    # 3. Currency Format Check (Hard Error only if provided and malformed)
    currency = expense.get("currency")
    if currency:
        curr_err = validate_currency(str(currency))
        if curr_err:
            errors.append(curr_err)
            
    # 4. Category Check (Hard Error)
    category = expense.get("category", "")
    valid_categories = ["Meals", "Travel", "Software", "Taxi", "Flight", "Hotel", "Restricted", "Other"]
    if category and category.capitalize() not in valid_categories:
        errors.append(f"Category '{category}' is unsupported. Must be one of {valid_categories}.")
        
    # 5. Arithmetic Check (Hard Error)
    items_list = expense.get("items_list", [])
    if items_list and isinstance(items_list, list):
        total_items_sum = 0.0
        for idx, item in enumerate(items_list):
            item_amount = item.get("amount", 0.0)
            if item_amount <= 0:
                errors.append(f"Invalid amount {item_amount} for item '{item.get('name', f'Item {idx+1}')}'. Must be positive.")
            total_items_sum += item_amount
        if amount is not None and abs(total_items_sum - float(amount)) > 0.01:
            errors.append(f"Arithmetic mismatch: Total amount {amount} does not equal the sum of itemized details {total_items_sum:.2f}.")
            
    # 6. Hallucination Check (Hard Error)
    if raw_text:
        hallucination_errors = check_hallucination(expense, raw_text)
        errors.extend(hallucination_errors)
        
    # 7. Duplicate Check within history (Hard Error)
    if history and expense.get("merchant") and expense.get("date") and expense.get("amount"):
        merchant_lower = str(expense.get("merchant")).lower()
        date_str = str(expense.get("date"))
        amt = float(expense.get("amount"))
        
        # Skip checking duplicates if values are Unknown
        if merchant_lower != "unknown" and date_str != "unknown":
            for past in history:
                if (str(past.get("merchant")).lower() == merchant_lower and 
                     str(past.get("date")) == date_str and 
                     abs(float(past.get("amount", 0)) - amt) < 0.01):
                    errors.append(f"Duplicate Claim Error: An identical expense from '{expense.get('merchant')}' on {date_str} for {expense.get('currency')} {amt:.2f} has already been submitted.")
                    break
                
    return errors

def validate_expenses(expenses: List[Dict[str, Any]], raw_text: str, history: List[Dict[str, Any]] = None, session_id: str = None) -> List[str]:
    if not expenses:
        if raw_text and not re.search(r"\d+", raw_text):
            return ["Validation Error: No expense items or numerical amounts detected in input."]
        return ["Validation Error: No expenses found to audit."]
        
    all_errors = []
    
    seen = set()
    for idx, exp in enumerate(expenses):
        exp_errors = validate_single_expense(exp, raw_text, history, session_id)
        if exp_errors:
            all_errors.extend([f"Expense #{idx+1}: {err}" for err in exp_errors])
            
        merchant = str(exp.get("merchant", "")).lower()
        date_val = str(exp.get("date", ""))
        amount = exp.get("amount", 0.0)
        
        if merchant and date_val and amount and merchant != "unknown" and date_val != "unknown":
            key = (merchant, date_val, float(amount))
            if key in seen:
                all_errors.append(f"Expense #{idx+1}: Duplicate claim detected within the same submission batch for merchant '{exp.get('merchant')}' on {date_val} for {amount}.")
            seen.add(key)
            
    return all_errors
