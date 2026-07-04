import os
import json
import datetime
from typing import Dict, Any, List, Tuple

def load_fraud_policy() -> Dict[str, Any]:
    policy_path = os.path.join(os.path.dirname(__file__), "fraud_policy.json")
    if os.path.exists(policy_path):
        try:
            with open(policy_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "weights": {
            "restricted_vendor": 40,
            "excessive_amount": 20,
            "weekend_anomaly": 15,
            "duplicate_claim_history": 30,
            "duplicate_claim_session": 30,
            "repeated_merchant_30days": 15,
            "just_under_threshold": 25,
            "manipulated_receipt": 60,
            "low_ocr_confidence": 20,
            "outlier_spending": 30,
            "fake_merchant": 20
        },
        "thresholds": {
            "review_limit_usd": 200.0,
            "review_limit_inr": 16600.0,
            "ocr_confidence_warning": 0.7,
            "high_risk_score": 60,
            "medium_risk_score": 30
        },
        "fake_merchant_keywords": ["test merchant", "dummy store", "fake corp", "unknown vendor", "sample store", "john doe"]
    }

def calculate_fraud_score(
    expense: Dict[str, Any], 
    history: List[Dict[str, Any]] = None,
    session_items: List[Dict[str, Any]] = None
) -> Tuple[int, str]:
    """
    Calculates a fraud risk score (0-100) for a given expense based on rules and history.
    
    Returns:
        Tuple: (fraud_score, reasoning)
    """
    policy = load_fraud_policy()
    weights = policy.get("weights", {})
    thresholds = policy.get("thresholds", {})
    fake_keywords = policy.get("fake_merchant_keywords", [])
    
    score = 0
    reasons = []
    
    merchant = str(expense.get("merchant", "Unknown"))
    amount = float(expense.get("amount", 0.0))
    currency = str(expense.get("currency", "USD")).upper()
    date_str = str(expense.get("date", ""))
    
    # 1. Restricted Vendor Check
    restricted_keywords = ["casino", "gambling", "club", "bar", "liquor", "pub", "lounge"]
    is_restricted = any(w in merchant.lower() for w in restricted_keywords)
    if is_restricted:
        score += weights.get("restricted_vendor", 40)
        reasons.append(f"Restricted vendor keyword matched (+{weights.get('restricted_vendor', 40)})")
        
    # 2. Fake Merchant Check
    is_fake = any(kw in merchant.lower() for kw in fake_keywords)
    if is_fake:
        score += weights.get("fake_merchant", 20)
        reasons.append(f"Fake or placeholder merchant name pattern (+{weights.get('fake_merchant', 20)})")
        
    # 3. Weekend Anomaly Check
    if date_str and date_str.lower() != "unknown":
        try:
            year, month, day = map(int, date_str.split("-"))
            dt = datetime.date(year, month, day)
            if dt.weekday() in [5, 6]:  # Saturday = 5, Sunday = 6
                score += weights.get("weekend_anomaly", 15)
                reasons.append(f"Expense claimed on weekend: {dt.strftime('%A')} (+{weights.get('weekend_anomaly', 15)})")
        except Exception:
            pass

    # 3b. Holiday Anomaly Check
    holidays = ["01-01", "07-04", "11-26", "12-25"]
    if date_str and len(date_str) >= 10:
        mm_dd = date_str[5:10]
        if mm_dd in holidays:
            score += weights.get("holiday_anomaly", 20)
            reasons.append(f"Expense claimed on holiday: {mm_dd} (+{weights.get('holiday_anomaly', 20)})")

    # 3c. Round Number Check
    if amount >= 50.0 and amount % 10.0 == 0.0:
        score += weights.get("round_number", 10)
        reasons.append(f"Round claim amount: {currency} {amount:.2f} (+{weights.get('round_number', 10)})")
            
    # 4. OCR Metadata Checks
    manipulated = expense.get("manipulated_receipt", False)
    if manipulated:
        score += weights.get("manipulated_receipt", 60)
        reasons.append(f"Edited or manipulated receipt detected (+{weights.get('manipulated_receipt', 60)})")
        
    ocr_confidence = expense.get("ocr_confidence_score", 1.0)
    warning_conf = thresholds.get("ocr_confidence_warning", 0.7)
    if ocr_confidence < warning_conf:
        score += weights.get("low_ocr_confidence", 20)
        reasons.append(f"Low OCR confidence ({ocr_confidence:.2f}) (+{weights.get('low_ocr_confidence', 20)})")
        
    # 5. Just Under Review Threshold Check
    limit_usd = thresholds.get("review_limit_usd", 200.0)
    limit_inr = thresholds.get("review_limit_inr", 16600.0)
    
    is_inr = (currency == "INR")
    threshold_val = limit_inr if is_inr else limit_usd
    
    # Check if amount is between 90% and 100% of review limit (e.g. $180 - $199.99)
    if threshold_val * 0.90 <= amount < threshold_val:
        score += weights.get("just_under_threshold", 25)
        reasons.append(f"Claim amount ({currency} {amount:.2f}) is suspiciously close to review threshold ({currency} {threshold_val}) (+{weights.get('just_under_threshold', 25)})")
        
    # 6. Duplicates and Split Check across History
    if history:
        exact_matches = 0
        repeated_30days = 0
        consecutive_split = 0
        
        for past in history:
            past_merchant = str(past.get("merchant", "")).lower()
            past_amount = float(past.get("amount", 0.0))
            past_date_str = str(past.get("date", ""))
            past_currency = str(past.get("currency", "USD")).upper()
            
            # Currency normalized comparisons
            if past_currency == currency:
                is_same_merchant = past_merchant == merchant.lower()
                is_same_amount = abs(past_amount - amount) < 0.01
                
                # Check exact duplicate (same merchant, amount, date)
                if is_same_merchant and is_same_amount and past_date_str == date_str:
                    exact_matches += 1
                    
                # Check repeated claim (same merchant, same amount within 30 days)
                if is_same_merchant and is_same_amount and date_str and past_date_str and date_str != "Unknown" and past_date_str != "Unknown":
                    try:
                        d1 = datetime.date.fromisoformat(date_str)
                        d2 = datetime.date.fromisoformat(past_date_str)
                        days_diff = abs((d1 - d2).days)
                        if 0 < days_diff <= 30:
                            repeated_30days += 1
                    except Exception:
                        pass
                        
                # Check split transaction: same merchant, same date (or consecutive days), different amounts
                if is_same_merchant and not is_same_amount and date_str and past_date_str and date_str != "Unknown" and past_date_str != "Unknown":
                    try:
                        d1 = datetime.date.fromisoformat(date_str)
                        d2 = datetime.date.fromisoformat(past_date_str)
                        days_diff = abs((d1 - d2).days)
                        if days_diff <= 1:
                            consecutive_split += 1
                    except Exception:
                        pass
                        
        if exact_matches > 0:
            score += weights.get("duplicate_claim_history", 30)
            reasons.append(f"Exact duplicate of {exact_matches} historical claim(s) (+{weights.get('duplicate_claim_history', 30)})")
        if repeated_30days > 0:
            score += weights.get("repeated_merchant_30days", 15)
            reasons.append(f"Identical amount submitted for '{merchant}' within 30 days (+{weights.get('repeated_merchant_30days', 15)})")
        if consecutive_split > 0:
            score += weights.get("duplicate_claim_session", 30)
            reasons.append(f"Potential split transaction: consecutive/same day claims at '{merchant}' (+{weights.get('duplicate_claim_session', 30)})")
            
    # 7. Batch session duplicate check
    if session_items:
        batch_exact = 0
        for other in session_items:
            # Don't check against self
            if other is expense:
                continue
            if (str(other.get("merchant", "")).lower() == merchant.lower() and
                str(other.get("date", "")) == date_str and
                abs(float(other.get("amount", 0.0)) - amount) < 0.01):
                batch_exact += 1
                
        if batch_exact > 0:
            score += weights.get("duplicate_claim_session", 30)
            reasons.append(f"Duplicate receipt matching another item in the same request batch (+{weights.get('duplicate_claim_session', 30)})")

    # 8. Impossible Travel Check
    def extract_city(text: str):
        from typing import Optional
        text_lower = text.lower()
        cities = ["boston", "paris", "new york", "london", "tokyo", "san francisco", "chicago"]
        for city in cities:
            if city in text_lower:
                return city
        return None

    raw_input = str(expense.get("raw_text", "")) or str(expense.get("merchant", ""))
    current_city = extract_city(raw_input)
    if current_city and date_str and date_str.lower() != "unknown" and history:
        try:
            curr_date = datetime.date.fromisoformat(date_str)
            for past in history:
                past_raw = str(past.get("raw_text", "")) or str(past.get("merchant", ""))
                past_city = extract_city(past_raw)
                past_date_str = str(past.get("date", ""))
                if past_city and past_city != current_city and past_date_str and past_date_str.lower() != "unknown":
                    past_date = datetime.date.fromisoformat(past_date_str)
                    days_diff = abs((curr_date - past_date).days)
                    if days_diff <= 1:
                        score += weights.get("impossible_travel", 35)
                        reasons.append(f"Impossible Travel: Claimed in {current_city.capitalize()} and {past_city.capitalize()} within {days_diff} day(s) (+{weights.get('impossible_travel', 35)})")
                        break
        except Exception:
            pass

    # Cap score at 100
    final_score = min(score, 100)
    reasoning_str = "; ".join(reasons) if reasons else "No suspicious anomalies detected."
    return final_score, reasoning_str
