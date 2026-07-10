"""Natural Language Understanding (NLU) Entity Extraction.

Regex-based, deterministic entity extraction with critical/optional field
classification and user role detection.  Zero LLM calls.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NLUResult:
    """Result of NLU entity extraction."""

    entities: dict[str, Any] = field(default_factory=dict)
    context_type: str = "unknown"
    confidence: float = 1.0
    missing_critical: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    user_role: str | None = None


# Critical fields per workflow intent
CRITICAL_FIELDS: dict[str, list[str]] = {
    "AUDIT": ["amount", "merchant"],
    "EXTRACT": ["amount", "merchant"],
    "POLICY": ["policy_reference"],
    "QUERY": ["query_param"],
    "CALCULATE": ["amount"],
}

OPTIONAL_FIELDS = ["date", "category", "department", "employee_id", "currency"]

# Known merchants for extraction
_KNOWN_MERCHANTS = [
    "uber",
    "lyft",
    "taxi",
    "hilton",
    "marriott",
    "starbucks",
    "mcdonalds",
    "burger king",
    "pizza hut",
    "subway",
    "delta",
    "united airlines",
    "american airlines",
    "southwest",
    "amazon",
    "walmart",
    "office depot",
    "staples",
]

# Role keywords
_ROLE_PATTERNS = {
    "manager": [r"\bmanager\b", r"\bas a manager\b", r"\bteam lead\b"],
    "employee": [r"\bemployee\b", r"\bas an employee\b", r"\bstaff\b"],
    "finance": [r"\bfinance\b", r"\baccountant\b", r"\bcfo\b", r"\bfinancial\b"],
    "admin": [r"\badmin\b", r"\badministrator\b", r"\bhr\b"],
}


class NLU:
    """Regex-based NLU entity extractor."""

    @staticmethod
    def extract_entities(text: str) -> NLUResult:
        """Extract entities from user input text.

        Returns an ``NLUResult`` with extracted entities, confidence, missing
        field classifications, and detected user role.
        """
        if not text or not text.strip():
            return NLUResult(confidence=0.0, context_type="empty")

        text_lower = text.lower().strip()
        entities: dict[str, Any] = {}

        # ---- Amount extraction ----
        amounts = NLU._extract_amounts(text_lower)
        if amounts:
            entities["amounts"] = amounts
            entities["amount"] = amounts[0]  # primary amount

        # ---- Currency extraction ----
        currency = NLU._extract_currency(text_lower)
        if currency:
            entities["currency"] = currency

        # ---- Date extraction ----
        dates = NLU._extract_dates(text)
        if dates:
            entities["dates"] = dates
            entities["date"] = dates[0]

        # ---- Merchant extraction ----
        merchants = NLU._extract_merchants(text_lower)
        if merchants:
            entities["merchants"] = merchants
            entities["merchant"] = merchants[0]

        # ---- Category extraction ----
        category = NLU._extract_category(text_lower)
        if category:
            entities["category"] = category

        # ---- Department extraction ----
        department = NLU._extract_department(text_lower)
        if department:
            entities["department"] = department

        # ---- Employee ID extraction ----
        emp_id = NLU._extract_employee_id(text_lower)
        if emp_id:
            entities["employee_id"] = emp_id

        # ---- Policy reference extraction ----
        policy_ref = NLU._extract_policy_reference(text_lower)
        if policy_ref:
            entities["policy_reference"] = policy_ref

        # ---- Query parameter detection ----
        if any(k in entities for k in ["department", "employee_id", "category"]):
            entities["query_param"] = True

        # ---- User role ----
        user_role = NLU._extract_user_role(text_lower)

        # ---- Context type ----
        context_type = NLU._determine_context_type(entities, text_lower)

        # ---- Confidence ----
        total_possible = 8  # amount, currency, date, merchant, category, dept, emp, policy
        found = sum(
            1
            for k in [
                "amount",
                "currency",
                "date",
                "merchant",
                "category",
                "department",
                "employee_id",
                "policy_reference",
            ]
            if k in entities
        )
        confidence = max(0.3, found / total_possible) if found > 0 else 0.3

        # ---- Missing fields (generic) ----
        missing_optional = [f for f in OPTIONAL_FIELDS if f not in entities]

        return NLUResult(
            entities=entities,
            context_type=context_type,
            confidence=round(confidence, 3),
            missing_critical=[],  # populated by planner per intent
            missing_optional=missing_optional,
            user_role=user_role,
        )

    @staticmethod
    def classify_missing_fields(nlu_result: NLUResult, workflow_intent: str) -> NLUResult:
        """Classify missing fields as critical or optional for the given intent.

        Modifies ``nlu_result.missing_critical`` in place and returns it.
        """
        critical = CRITICAL_FIELDS.get(workflow_intent, [])
        nlu_result.missing_critical = [f for f in critical if f not in nlu_result.entities]
        nlu_result.missing_optional = [f for f in OPTIONAL_FIELDS if f not in nlu_result.entities]
        return nlu_result

    # ------------------------------------------------------------------
    # Private extractors
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_amounts(text: str) -> list[float]:
        """Extract monetary amounts from text."""
        amounts: list[float] = []
        # Match patterns like $150, 150.50, ₹200, etc.
        for match in re.finditer(r"[\$₹£€]?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", text):
            try:
                val = float(match.group(1).replace(",", ""))
                if 0 < val < 10_000_000:  # reasonable expense range
                    amounts.append(val)
            except ValueError:
                continue
        return amounts

    @staticmethod
    def _extract_currency(text: str) -> str | None:
        """Extract currency from text."""
        if "₹" in text or "inr" in text:
            return "INR"
        if "€" in text or "eur" in text:
            return "EUR"
        if "£" in text or "gbp" in text:
            return "GBP"
        if "$" in text or "usd" in text:
            return "USD"
        return None

    @staticmethod
    def _extract_dates(text: str) -> list[str]:
        """Extract dates in YYYY-MM-DD format."""
        return re.findall(r"\d{4}-\d{2}-\d{2}", text)

    @staticmethod
    def _extract_merchants(text: str) -> list[str]:
        """Extract known merchant names from text."""
        found: list[str] = []
        for merchant in _KNOWN_MERCHANTS:
            if merchant in text:
                found.append(merchant.title())
        return found

    @staticmethod
    def _extract_category(text: str) -> str | None:
        """Extract expense category from text."""
        categories = {
            "meal": "Meals",
            "food": "Meals",
            "lunch": "Meals",
            "dinner": "Meals",
            "breakfast": "Meals",
            "hotel": "Hotel",
            "stay": "Hotel",
            "accommodation": "Hotel",
            "flight": "Travel",
            "travel": "Travel",
            "taxi": "Travel",
            "uber": "Travel",
            "transport": "Travel",
            "cab": "Travel",
            "office": "Office Supplies",
            "supplies": "Office Supplies",
            "equipment": "Equipment",
        }
        for keyword, cat in categories.items():
            if keyword in text:
                return cat

        # Merchant fallback
        merchant_cats = {
            "hilton": "Hotel",
            "marriott": "Hotel",
            "uber": "Travel",
            "lyft": "Travel",
            "taxi": "Travel",
            "starbucks": "Meals",
            "mcdonalds": "Meals",
            "burger king": "Meals",
            "pizza hut": "Meals",
            "subway": "Meals",
            "delta": "Travel",
            "united": "Travel",
            "american": "Travel",
            "southwest": "Travel",
        }
        for merchant, cat in merchant_cats.items():
            if merchant in text:
                return cat

        return None

    @staticmethod
    def _extract_department(text: str) -> str | None:
        """Extract department name from text."""
        departments = {
            "engineering": "Engineering",
            "sales": "Sales",
            "marketing": "Marketing",
            "hr": "HR",
            "finance": "Finance",
            "operations": "Operations",
            "legal": "Legal",
            "it": "IT",
        }
        for keyword, dept in departments.items():
            if re.search(rf"\b{keyword}\b", text):
                return dept
        return None

    @staticmethod
    def _extract_employee_id(text: str) -> str | None:
        """Extract employee ID like EMP101."""
        match = re.search(r"\b(emp\d+)\b", text, re.IGNORECASE)
        return match.group(1).upper() if match else None

    @staticmethod
    def _extract_policy_reference(text: str) -> str | None:
        """Extract policy-related references from text."""
        policy_keywords = [
            "meal limit",
            "hotel limit",
            "travel limit",
            "spending limit",
            "reimbursement policy",
            "travel policy",
            "expense policy",
            "company policy",
            "policy",
            "limit",
            "rules",
            "allowed",
        ]
        for kw in policy_keywords:
            if kw in text:
                return kw
        return None

    @staticmethod
    def _extract_user_role(text: str) -> str | None:
        """Detect user role from text."""
        for role, patterns in _ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return role
        return None

    @staticmethod
    def _determine_context_type(entities: dict[str, Any], text: str) -> str:
        """Determine the context type based on extracted entities."""
        if "amount" in entities and "merchant" in entities:
            return "expense_submission"
        if "amount" in entities:
            return "financial_query"
        if "policy_reference" in entities:
            return "policy_inquiry"
        if "department" in entities or "employee_id" in entities:
            return "data_query"
        return "general"
