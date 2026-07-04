from typing import Dict, Any, List, Tuple
from app.services.base_service import BaseService

class ReasoningService(BaseService):
    """Business service performing currency conversion and arithmetic validations."""

    def __init__(self):
        # Default conversion rates to USD (multiplication factor)
        self.exchange_rates = {
            "EUR": 1.10,
            "GBP": 1.30,
            "INR": 0.012,
            "CAD": 0.74,
            "AUD": 0.66,
            "JPY": 0.0065,
            "USD": 1.0,
        }

    def convert_to_usd(self, amount: float, from_currency: str) -> float:
        """Converts an amount to USD using exchange rates."""
        rate = self.exchange_rates.get(from_currency.upper(), 1.0)
        return amount * rate

    def convert_from_usd(self, amount: float, to_currency: str) -> float:
        """Converts an amount from USD to target currency."""
        rate = self.exchange_rates.get(to_currency.upper(), 1.0)
        if rate == 0:
            return amount
        return amount / rate

    def verify_arithmetic(self, claimed: float, reimbursable: float, rejected: float) -> bool:
        """Enforces that claimed amount equals reimbursable + rejected."""
        return abs(claimed - (reimbursable + rejected)) < 0.01

    def calculate_reimbursement(
        self,
        claimed: float,
        limit: float,
        multiplier: float = 1.0,
        doubled_limit: bool = False
    ) -> Tuple[float, float]:
        """Calculates allowed reimbursable and rejected portions.

        Args:
            claimed: Claimed amount.
            limit: The policy limit.
            multiplier: The role multiplier.
            doubled_limit: True if policy exception doubles the limit.

        Returns:
            Tuple: (reimbursable, rejected)
        """
        effective_limit = limit * multiplier
        if doubled_limit:
            effective_limit *= 2.0
            
        if claimed <= effective_limit:
            return claimed, 0.0
        return effective_limit, claimed - effective_limit
