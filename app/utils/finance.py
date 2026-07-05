import math
from typing import Dict, Any, List, Optional

def safe_round(val: float) -> float:
    """Rounds float values to 2 decimal places to prevent floating-point drift."""
    if val is None:
        return 0.0
    return round(val, 2)

def safe_add(*args: float) -> float:
    """Sums values safely, rounding to 2 decimal places."""
    return safe_round(sum(safe_round(x) for x in args if x is not None))

def safe_sub(a: float, b: float) -> float:
    """Subtracts values safely, rounding to 2 decimal places."""
    return safe_round(safe_round(a) - safe_round(b))

def convert_currency(amount: float, from_curr: str, to_curr: str, rates: Dict[str, float]) -> float:
    """Converts amount from from_curr to to_curr using base-USD conversion.
    
    Rates dict maps foreign currency code to USD value (e.g. INR = 0.012 USD).
    """
    amount = safe_round(amount)
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    
    if from_curr == to_curr:
        return amount

    # Convert to USD first
    if from_curr == "USD":
        usd_amount = amount
    else:
        usd_amount = amount * rates.get(from_curr, 1.0)

    # Convert USD to target currency
    if to_curr == "USD":
        converted = usd_amount
    else:
        target_rate = rates.get(to_curr, 1.0)
        converted = usd_amount / target_rate if target_rate > 0 else usd_amount

    return safe_round(converted)

def calculate_calibrated_confidence(
    intent_conf: float,
    ocr_conf: float,
    field_confs: List[float]
) -> float:
    """Calculates a calibrated confidence score between 0.0 and 1.0.
    
    Uses product of confidence scores to ensure that if any critical step 
    is low confidence, the overall decision confidence drops significantly.
    """
    conf = float(intent_conf) * float(ocr_conf)
    for fc in field_confs:
        if fc is not None:
            conf *= float(fc)
    return safe_round(conf)
