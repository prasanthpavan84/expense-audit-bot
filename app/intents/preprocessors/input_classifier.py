"""Input Type Classifier — classifies the *kind* of input before intent detection.

Input type is NOT the same as intent.  For example:
  - Input type ``RECEIPT`` may map to intent ``AUDIT`` or ``EXTRACT``.
  - Input type ``CHAT`` may map to intent ``GREETING``.

This drastically reduces false audit triggers by catching noise, code,
JSON, and other non-natural-language inputs before they ever reach the
intent engine.  Zero LLM calls.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class InputType(str, Enum):
    """Exhaustive input type taxonomy."""
    EMPTY = "EMPTY"
    WHITESPACE = "WHITESPACE"
    NOISE = "NOISE"
    PUNCTUATION = "PUNCTUATION"
    NUMBER = "NUMBER"
    SHORT_TEXT = "SHORT_TEXT"
    GREETING = "GREETING"
    CHAT = "CHAT"
    QUESTION = "QUESTION"
    COMMAND = "COMMAND"
    OCR = "OCR"
    RECEIPT = "RECEIPT"
    IMAGE_REFERENCE = "IMAGE_REFERENCE"
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    CODE = "CODE"
    TABLE = "TABLE"
    CSV = "CSV"
    URL = "URL"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class InputTypeResult:
    """Immutable result of input type classification."""
    input_type: InputType
    confidence: float
    reason: str


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------
# Only ASCII punctuation/symbols — NOT unicode emoji
_ONLY_PUNCT_RE = re.compile(r'^[\s!@#$%^&*()\-_=+\[\]{}|;:,.<>?/~`\'"\\\\]+$')
_ONLY_DIGITS_RE = re.compile(r"^[\d\s.,]+$")
_ONLY_EMOJI_RE = re.compile(
    r"^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    r"\U00002702-\U000027B0\U000024C2-\U0001F251"
    r"\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    r"\s]+$",
    re.UNICODE,
)
# Keyboard smash: repeated single char OR known smash rows, but exclude
# real English words by checking against a small allowlist.
_KEYBOARD_SMASH_RE = re.compile(r"^([a-z])\1{3,}$", re.I)
_SMASH_ROW_RE = re.compile(r"^[asdfghjkl]{5,}$|^[qwertyuiop]{6,}$|^[zxcvbnm]{5,}$", re.I)
_JSON_RE = re.compile(r"^\s*[\[{].*[\]}]\s*$", re.DOTALL)
_MARKDOWN_RE = re.compile(r"^#{1,6}\s|^\*{1,3}\s|\*\*[^*]+\*\*|^-\s", re.MULTILINE)
_CODE_RE = re.compile(
    r"(def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import"
    r"|function\s+\w+|console\.log|System\.out|SELECT\s+\w+\s+FROM"
    r"|CREATE\s+TABLE|INSERT\s+INTO|var\s+\w+\s*=)",
    re.I,
)
_URL_RE = re.compile(r"^https?://\S+$", re.I)
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^[\+]?[\d\s\-().]{7,15}$")
_TABLE_RE = re.compile(r"\|.*\|.*\|", re.MULTILINE)
_CSV_RE = re.compile(r"^[^,\n]+,[^,\n]+(,[^,\n]+)*$", re.MULTILINE)
_IMAGE_REF_RE = re.compile(
    r"\b(image|photo|picture|screenshot|scan|attachment|jpg|png|pdf|upload)\b",
    re.I,
)
_GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|howdy|hola|greetings|good\s*(morning|afternoon|evening|night)|namaste|yo)\s*[!.?]*\s*$",
    re.I,
)

# Receipt indicators (merchant, amount, tax, total, date, payment, etc.)
_RECEIPT_INDICATORS = [
    re.compile(r"\btotal\b", re.I),
    re.compile(r"\bsubtotal\b", re.I),
    re.compile(r"\btax\b", re.I),
    re.compile(r"\bgst\b", re.I),
    re.compile(r"\bvat\b", re.I),
    re.compile(r"\binvoice\b", re.I),
    re.compile(r"\breceipt\b", re.I),
    re.compile(r"[\$\u20b9\u00a3\u20ac]\s*\d", re.I),
    re.compile(r"\bpayment\b", re.I),
    re.compile(r"\bchange\s+due\b", re.I),
    re.compile(r"\bcard\b.*\b\d{4}\b", re.I),
]

_OCR_INDICATORS = [
    re.compile(r"[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}"),  # all-caps blocks
    re.compile(r"\d{2}[/\-]\d{2}[/\-]\d{2,4}"),  # dates
    re.compile(r"[Il1]{3,}"),  # OCR confusion between I/l/1
    re.compile(r"[O0]{3,}"),  # OCR confusion between O/0
]

# Single-char inputs that are obviously not expense requests
_SINGLE_CHAR_NON_EXPENSE = set("abcdefghijklmnopqrstuvwxyz")


class InputClassifier:
    """Deterministic input type classifier — runs before intent detection."""

    @staticmethod
    def classify(text: str) -> InputTypeResult:
        """Classify the type of user input.  Not the intent."""
        # --- Empty / whitespace ---
        if not text:
            return InputTypeResult(InputType.EMPTY, 1.0, "No input provided")
        stripped = text.strip()
        if not stripped:
            return InputTypeResult(InputType.WHITESPACE, 1.0, "Input is only whitespace")

        length = len(stripped)

        # --- Pure emoji (check BEFORE punctuation since \W matches emoji) ---
        if _ONLY_EMOJI_RE.fullmatch(stripped):
            return InputTypeResult(InputType.NOISE, 0.95, "Input is only emoji")

        # --- Pure punctuation ---
        if _ONLY_PUNCT_RE.fullmatch(stripped):
            return InputTypeResult(InputType.PUNCTUATION, 1.0, "Input is only punctuation/symbols")

        # --- Pure digits ---
        if _ONLY_DIGITS_RE.fullmatch(stripped):
            return InputTypeResult(InputType.NUMBER, 0.95, "Input is only numeric")

        # --- Single character ---
        if length == 1:
            return InputTypeResult(InputType.SHORT_TEXT, 0.90, "Single character input")

        # --- Keyboard smash (repeated char or known smash rows) ---
        if length <= 20 and (_KEYBOARD_SMASH_RE.fullmatch(stripped) or _SMASH_ROW_RE.fullmatch(stripped)):
            return InputTypeResult(InputType.NOISE, 0.95, "Keyboard smash detected")

        # --- URL ---
        if _URL_RE.fullmatch(stripped):
            return InputTypeResult(InputType.URL, 0.95, "Input is a URL")

        # --- Email ---
        if _EMAIL_RE.fullmatch(stripped):
            return InputTypeResult(InputType.EMAIL, 0.95, "Input is an email address")

        # --- Phone ---
        if _PHONE_RE.fullmatch(stripped):
            return InputTypeResult(InputType.PHONE, 0.90, "Input appears to be a phone number")

        # --- JSON ---
        if _JSON_RE.fullmatch(stripped):
            return InputTypeResult(InputType.JSON, 0.90, "Input looks like JSON")

        # --- Code ---
        if _CODE_RE.search(stripped):
            return InputTypeResult(InputType.CODE, 0.85, "Input contains code patterns")

        # --- Markdown ---
        if _MARKDOWN_RE.search(stripped) and length > 10:
            return InputTypeResult(InputType.MARKDOWN, 0.80, "Input contains markdown formatting")

        # --- Table ---
        if _TABLE_RE.search(stripped):
            return InputTypeResult(InputType.TABLE, 0.80, "Input contains table formatting")

        # --- CSV ---
        if _CSV_RE.search(stripped) and "," in stripped and length > 10:
            return InputTypeResult(InputType.CSV, 0.75, "Input looks like CSV data")

        # --- Greeting (standalone) ---
        if _GREETING_RE.fullmatch(stripped):
            return InputTypeResult(InputType.GREETING, 0.95, "Standalone greeting detected")

        # --- Receipt indicators ---
        receipt_score = sum(1 for pat in _RECEIPT_INDICATORS if pat.search(stripped))
        if receipt_score >= 3:
            return InputTypeResult(InputType.RECEIPT, min(0.50 + receipt_score * 0.10, 0.98),
                                   f"Receipt indicators: {receipt_score} matches")

        # --- OCR-like text ---
        ocr_score = sum(1 for pat in _OCR_INDICATORS if pat.search(stripped))
        if ocr_score >= 2:
            return InputTypeResult(InputType.OCR, min(0.50 + ocr_score * 0.15, 0.95),
                                   f"OCR indicators: {ocr_score} matches")

        # --- Image reference ---
        if _IMAGE_REF_RE.search(stripped):
            return InputTypeResult(InputType.IMAGE_REFERENCE, 0.70, "Image reference detected")

        # --- Question ---
        if stripped.endswith("?") or stripped.lower().startswith(("what ", "who ", "how ", "why ", "when ", "where ", "is ", "can ", "do ", "does ")):
            return InputTypeResult(InputType.QUESTION, 0.75, "Input is a question")

        # --- Command ---
        if stripped.lower().startswith(("please ", "could you ", "can you ", "i need ", "i want ")):
            return InputTypeResult(InputType.COMMAND, 0.70, "Input is a command/request")

        # --- Short text (2-3 chars, likely noise) ---
        if length <= 3 and stripped.lower() in _SINGLE_CHAR_NON_EXPENSE:
            return InputTypeResult(InputType.SHORT_TEXT, 0.85, "Very short non-expense text")

        # --- Chat (general text) ---
        if length < 50 and not any(c.isdigit() for c in stripped):
            return InputTypeResult(InputType.CHAT, 0.60, "Short text without financial data")

        # --- Default to UNKNOWN ---
        return InputTypeResult(InputType.UNKNOWN, 0.50, "Input type could not be determined")
