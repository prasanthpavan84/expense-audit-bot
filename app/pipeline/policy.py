from .parser import ExpenseObject


class PolicyEngine:
    """Simple policy engine.
    Checks department-level limits. Hardcoded for demo.
    """

    def __init__(self, limits: dict[str, float] | None = None):
        self.limits = limits or {"default": 5000.0}

    def check_limits(self, expense: ExpenseObject) -> bool:
        """Return True if the expense amount is within the configured limit."""
        limit = self.limits.get(expense.merchant.lower(), self.limits["default"])
        return expense.amount <= limit

    def evaluate(self, expense: ExpenseObject) -> dict[str, bool]:
        """Return a dict of policy checks."""
        return {
            "within_limit": self.check_limits(expense),
        }
