from datetime import datetime
from .parser import ExpenseObject


def _get_val(o, attr, default=None):
    if isinstance(o, dict):
        return o.get(attr, default)
    return getattr(o, attr, default)


def _parse_date(d) -> datetime | None:
    if isinstance(d, datetime):
        return d
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d)
        except Exception:
            pass
    return None


def detect_duplicate_receipt(expense: ExpenseObject, recent_expenses: list) -> bool:
    # 1. If both have receipt_image, compare them
    expense_image = expense.receipt_image
    for prev in recent_expenses:
        prev_image = _get_val(prev, "receipt_image")
        if expense_image and prev_image and expense_image == prev_image:
            return True

    # 2. Or fallback to matching merchant, amount, and date
    expense_date = _parse_date(expense.date)
    for prev in recent_expenses:
        prev_merchant = _get_val(prev, "merchant")
        prev_amount = _get_val(prev, "amount")
        prev_date = _parse_date(_get_val(prev, "date"))

        merchant_matches = (prev_merchant == expense.merchant)
        amount_matches = (float(prev_amount or 0) == float(expense.amount or 0))

        date_matches = False
        if expense_date and prev_date:
            date_matches = (expense_date.date() == prev_date.date())
        elif expense_date is None and prev_date is None:
            date_matches = True

        if merchant_matches and amount_matches and date_matches:
            return True

    return False


def detect_split_expense(expense: ExpenseObject, recent_expenses: list) -> bool:
    threshold = 3
    window_days = 2
    expense_date = _parse_date(expense.date)

    count = 0
    for prev in recent_expenses:
        prev_merchant = _get_val(prev, "merchant")
        if prev_merchant != expense.merchant:
            continue

        prev_date = _parse_date(_get_val(prev, "date"))
        if expense_date and prev_date:
            if abs((expense_date - prev_date).days) <= window_days:
                count += 1
        elif expense_date == prev_date:
            count += 1

    return count >= threshold


def detect_amount_anomaly(expense: ExpenseObject, historical_average: float) -> bool:
    if historical_average <= 0:
        return False
    return expense.amount > 3 * historical_average


def run_fraud_checks(
    expense: ExpenseObject, recent_expenses: list, historical_average: float
) -> dict[str, bool]:
    return {
        "duplicate_receipt": detect_duplicate_receipt(expense, recent_expenses),
        "split_expense": detect_split_expense(expense, recent_expenses),
        "amount_anomaly": detect_amount_anomaly(expense, historical_average),
    }


class FraudEngine:
    """Facade class exposing the fraud detection API used by the pipeline."""

    def __init__(self):
        pass

    def run(
        self, expense: ExpenseObject, recent_expenses: list, historical_average: float
    ) -> dict[str, bool]:
        return run_fraud_checks(expense, recent_expenses, historical_average)
