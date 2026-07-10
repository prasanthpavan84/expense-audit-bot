import re

from app.core.agent_base import BaseExpenseAgent
from app.models.state import WorkflowState


class SecurityAgent(BaseExpenseAgent):
    def __init__(self):
        super().__init__(name="security_agent", system_instruction="Guard against PII leak and prompt injection")

    async def process_state(self, state: WorkflowState) -> WorkflowState:
        text = state.raw_input
        scrubbed_text = text
        pii_found = []

        # 1. Credit Cards (Luhn Check)
        cc_regex = r"\b(?:\d[ -]*?){13,19}\b"

        def is_valid_luhn(card_number: str) -> bool:
            digits = [int(d) for d in re.sub(r"\D", "", card_number)]
            if len(digits) < 13 or len(digits) > 19:
                return False
            checksum = 0
            reverse_digits = digits[::-1]
            for i, digit in enumerate(reverse_digits):
                if i % 2 == 1:
                    double_digit = digit * 2
                    if double_digit > 9:
                        double_digit -= 9
                    checksum += double_digit
                else:
                    checksum += digit
            return checksum % 10 == 0

        def cc_replacer(match):
            val = match.group(0)
            clean_val = re.sub(r"\D", "", val)
            if is_valid_luhn(clean_val):
                pii_found.append("credit_card")
                return "[REDACTED_CREDIT_CARD]"
            return val

        scrubbed_text = re.sub(cc_regex, cc_replacer, scrubbed_text)

        # 2. Email Address
        email_regex = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
        if re.search(email_regex, scrubbed_text):
            scrubbed_text = re.sub(email_regex, "[REDACTED_EMAIL]", scrubbed_text)
            pii_found.append("email")

        # 3. Social Security Number
        ssn_regex = r"\b\d{3}-\d{2}-\d{4}\b"
        if re.search(ssn_regex, scrubbed_text):
            scrubbed_text = re.sub(ssn_regex, "[REDACTED_SSN]", scrubbed_text)
            pii_found.append("ssn")

        # Prompt Injection Detection
        injection_keywords = [
            "ignore previous instructions",
            "system prompt",
            "you are now",
            "override policy",
            "jailbreak",
            "dan mode",
            "update limit",
            "change limit",
            "bypass policy",
            "override limit",
            "approve this regardless",
            "admin override",
        ]
        injection_detected = False
        matched_keyword = None
        for keyword in injection_keywords:
            if keyword in text.lower():
                injection_detected = True
                matched_keyword = keyword
                break

        # Repeated words check
        if not injection_detected:
            if re.search(r"(\b\w+\b)(?:\s+\1){4,}", text.lower()):
                injection_detected = True
                matched_keyword = "repeated tokens"

        # Control characters
        if not injection_detected:
            has_control = False
            for char in text:
                o = ord(char)
                if o < 32 and char not in "\r\n\t":
                    has_control = True
                    break
            if has_control or any(esc in text for esc in ["\\u0000", "\\u0001", "\\u0002", "\\x00", "\\x01", "\\x02"]):
                injection_detected = True
                matched_keyword = "malicious unicode / control characters"

        # Prohibited purchase terms
        prohibited_keywords = ["bribe", "kickback", "payoff", "ransom"]
        prohibited_detected = False
        matched_prohibited = None
        for keyword in prohibited_keywords:
            if keyword in text.lower():
                prohibited_detected = True
                matched_prohibited = keyword
                break

        # Apply redactions
        state.raw_input = scrubbed_text
        if pii_found:
            state.metadata["pii_scrubbed"] = pii_found

        # Set block flags
        if injection_detected:
            state.metadata["security_error"] = (
                f"CRITICAL: Prompt injection attempt detected and blocked ({matched_keyword})."
            )
            state.metadata["validation_errors"] = [state.metadata["security_error"]]
        elif prohibited_detected:
            state.metadata["security_error"] = f"DENIED: Prohibited term '{matched_prohibited}' found in submission."
            state.metadata["validation_errors"] = [state.metadata["security_error"]]

        return state
