import datetime
from typing import Any

from app.plugins.base_plugin import BasePlugin


class DuplicatePlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Duplicate & Split Claim Analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "Enterprise Security Core"

    @property
    def priority(self) -> int:
        return 1

    @property
    def description(self) -> str:
        return "Detects exact duplicate submissions, splits, or identical claims within 30 days."

    def check(
        self, expense: dict[str, Any], history: list[dict[str, Any]] = None, session_items: list[dict[str, Any]] = None
    ) -> tuple[int, str]:
        score = 0
        reasons = []

        merchant = str(expense.get("merchant", "Unknown")).lower()
        amount = float(expense.get("amount", 0.0))
        date_str = str(expense.get("date", ""))
        currency = str(expense.get("currency", "USD")).upper()

        if history:
            exact_matches = 0
            repeated_30days = 0
            consecutive_split = 0

            for past in history:
                past_merchant = str(past.get("merchant", "")).lower()
                past_amount = float(past.get("amount", 0.0))
                past_date_str = str(past.get("date", ""))
                past_currency = str(past.get("currency", "USD")).upper()

                if past_currency == currency:
                    is_same_merchant = past_merchant == merchant
                    is_same_amount = abs(past_amount - amount) < 0.01

                    if is_same_merchant and is_same_amount and past_date_str == date_str:
                        exact_matches += 1

                    if (
                        is_same_merchant
                        and is_same_amount
                        and date_str
                        and past_date_str
                        and date_str != "Unknown"
                        and past_date_str != "Unknown"
                    ):
                        try:
                            d1 = datetime.date.fromisoformat(date_str)
                            d2 = datetime.date.fromisoformat(past_date_str)
                            if 0 < abs((d1 - d2).days) <= 30:
                                repeated_30days += 1
                        except Exception:
                            pass

                    if (
                        is_same_merchant
                        and not is_same_amount
                        and date_str
                        and past_date_str
                        and date_str != "Unknown"
                        and past_date_str != "Unknown"
                    ):
                        try:
                            d1 = datetime.date.fromisoformat(date_str)
                            d2 = datetime.date.fromisoformat(past_date_str)
                            if abs((d1 - d2).days) <= 1:
                                consecutive_split += 1
                        except Exception:
                            pass

            if exact_matches > 0:
                score += 30
                reasons.append(f"Exact duplicate of {exact_matches} historical claim(s) (+30)")
            if repeated_30days > 0:
                score += 15
                reasons.append(f"Identical amount submitted for '{expense.get('merchant')}' within 30 days (+15)")
            if consecutive_split > 0:
                score += 30
                reasons.append(
                    f"Potential split transaction: consecutive/same day claims at '{expense.get('merchant')}' (+30)"
                )

        if session_items:
            batch_exact = 0
            for other in session_items:
                if other is expense:
                    continue
                if (
                    str(other.get("merchant", "")).lower() == merchant
                    and str(other.get("date", "")) == date_str
                    and abs(float(other.get("amount", 0.0)) - amount) < 0.01
                ):
                    batch_exact += 1
            if batch_exact > 0:
                score += 30
                reasons.append("Duplicate receipt matching another item in the same batch (+30)")

        return score, "; ".join(reasons)
