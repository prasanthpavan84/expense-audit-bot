from typing import Any

from app.plugins.base_plugin import BasePlugin


class VendorPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Prohibited & Fake Vendor Assessor"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "Enterprise Security Core"

    @property
    def priority(self) -> int:
        return 2

    @property
    def description(self) -> str:
        return "Checks if expenditures belong to restricted keywords or fake vendor identifiers."

    def check(
        self, expense: dict[str, Any], history: list[dict[str, Any]] = None, session_items: list[dict[str, Any]] = None
    ) -> tuple[int, str]:
        score = 0
        reasons = []

        merchant = str(expense.get("merchant", "Unknown")).lower()

        # Prohibited keywords check
        restricted_keywords = ["casino", "gambling", "club", "bar", "liquor", "pub", "lounge"]
        is_restricted = any(w in merchant for w in restricted_keywords)
        if is_restricted:
            score += 40
            reasons.append("Restricted vendor keyword matched (+40)")

        # Fake Merchant names check
        fake_keywords = ["test merchant", "dummy store", "fake corp", "unknown vendor", "sample store", "john doe"]
        is_fake = any(kw in merchant for kw in fake_keywords)
        if is_fake:
            score += 20
            reasons.append("Fake or placeholder merchant name pattern (+20)")

        return score, "; ".join(reasons)
