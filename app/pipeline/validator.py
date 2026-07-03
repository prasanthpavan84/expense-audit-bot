import re
from datetime import datetime
from typing import List

from .parser import Expense

class ValidationError(Exception):
    """Raised when an expense fails validation."""
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field
        self.message = message
    def __str__(self):  # pragma: no cover
        return f'ValidationError(field={self.field}): {self.message}'

class Validator:
    """Stateless validator for Expense objects."""
    CURRENCY_REGEX = re.compile(r'^[A-Z]{3}$')
    MAX_FUTURE_DAYS = 30

    @classmethod
    def validate(cls, expense: Expense) -> Expense:
        if not expense.employee_id or not isinstance(expense.employee_id, str):
            raise ValidationError('employee_id must be a non‑empty string', 'employee_id')
        if not expense.merchant or not isinstance(expense.merchant, str):
            raise ValidationError('merchant must be a non‑empty string', 'merchant')
        if not isinstance(expense.amount, (int, float)) or expense.amount <= 0:
            raise ValidationError('amount must be a positive number', 'amount')
        if not isinstance(expense.currency, str) or not cls.CURRENCY_REGEX.match(expense.currency):
            raise ValidationError('currency must be a 3‑letter ISO code', 'currency')
        if not isinstance(expense.date, datetime):
            raise ValidationError('date must be a datetime object', 'date')
        now = datetime.utcnow()
        delta = expense.date - now
        if delta.days > cls.MAX_FUTURE_DAYS:
            raise ValidationError(f'date cannot be more than {cls.MAX_FUTURE_DAYS} days in the future', 'date')
        if expense.receipt_image is not None:
            if not isinstance(expense.receipt_image, str) or not expense.receipt_image.strip():
                raise ValidationError('receipt_image must be a non‑empty base64 string', 'receipt_image')
        return expense


def validate_expense(expense: Expense) -> Expense:
    """Convenient wrapper for pipeline imports.

    Calls :class:`Validator.validate` and returns the validated expense.
    """
    return Validator.validate(expense)
