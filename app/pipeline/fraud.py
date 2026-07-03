from .parser import ExpenseObject
from typing import List, Dict

def detect_duplicate_receipt(expense: ExpenseObject, recent_expenses: List[ExpenseObject]) -> bool:
    if not expense.receipt_image:
        return False
    return any(prev.receipt_image == expense.receipt_image for prev in recent_expenses if prev.receipt_image)

def detect_split_expense(expense: ExpenseObject, recent_expenses: List[ExpenseObject]) -> bool:
    threshold = 3
    window_days = 2
    count = sum(1 for prev in recent_expenses
                if prev.merchant == expense.merchant and abs((expense.date - prev.date).days) <= window_days)
    return count >= threshold

def detect_amount_anomaly(expense: ExpenseObject, historical_average: float) -> bool:
    if historical_average <= 0:
        return False
    return expense.amount > 3 * historical_average

def run_fraud_checks(expense: ExpenseObject, recent_expenses: List[ExpenseObject], historical_average: float) -> Dict[str, bool]:
    return {
        "duplicate_receipt": detect_duplicate_receipt(expense, recent_expenses),
        "split_expense": detect_split_expense(expense, recent_expenses),
        "amount_anomaly": detect_amount_anomaly(expense, historical_average),
    }

class FraudEngine:
    """Facade class exposing the fraud detection API used by the pipeline."""
    def __init__(self):
        pass

    def run(self, expense: ExpenseObject, recent_expenses: List[ExpenseObject], historical_average: float) -> Dict[str, bool]:
        return run_fraud_checks(expense, recent_expenses, historical_average)
