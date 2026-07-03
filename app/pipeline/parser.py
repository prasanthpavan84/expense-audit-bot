import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass
class ExpenseObject:
    employee_id: str
    merchant: str
    amount: float
    currency: str
    date: datetime
    receipt_image: str | None = None
    raw: Dict[str, Any] | None = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ExpenseObject":
        """Parse a raw request dict into an :class:`ExpenseObject`.

        Minimal validation; unknown fields stored in ``raw``.
        """
        employee_id = data.get("employee_id", "")
        merchant = data.get("merchant", "")
        amount = float(data.get("amount", 0))
        currency = data.get("currency", "USD")
        date_str = data.get("date", "")
        try:
            date = datetime.fromisoformat(date_str)
        except Exception:
            date = datetime.utcnow()
        receipt_image = data.get("receipt_image")
        raw = {k: v for k, v in data.items() if k not in {
            "employee_id",
            "merchant",
            "amount",
            "currency",
            "date",
            "receipt_image",
        }}
        return ExpenseObject(
            employee_id=employee_id,
            merchant=merchant,
            amount=amount,
            currency=currency,
            date=date,
            receipt_image=receipt_image,
            raw=raw,
        )

def parse_expense(raw_data: Dict[str, Any]) -> ExpenseObject:
    """Public entry point for pipeline parsing."""
    return ExpenseObject.from_dict(raw_data)

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass
class Expense:
    employee_id: str
    merchant: str
    amount: float
    currency: str
    date: datetime
    receipt_image: str | None = None
    raw: Dict[str, Any] | None = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Expense':
        employee_id = data.get('employee_id', '')
        merchant = data.get('merchant', '')
        amount = float(data.get('amount', 0))
        currency = data.get('currency', 'USD')
        date_str = data.get('date', '')
        try:
            date = datetime.fromisoformat(date_str)
        except Exception:
            date = datetime.utcnow()
        receipt_image = data.get('receipt_image')
        raw = {k: v for k, v in data.items() if k not in {'employee_id','merchant','amount','currency','date','receipt_image'}}
        return Expense(employee_id, merchant, amount, currency, date, receipt_image, raw)
