"""Regex Classifier — uses regex patterns for intent detection.

Provides strong signal for structured inputs like receipt data,
policy questions, and financial queries.
"""

import re
from app.intents.classifiers.base import BaseIntentClassifier, ClassifierVote

# Stage 2 intent → list of compiled regex patterns
_PATTERNS = {
    # --- Conversation ---
    "GREETING": {
        "stage1": "Conversation",
        "patterns": [
            re.compile(r"^\s*(hi|hello|hey|howdy|hola|greetings|namaste|yo)\s*[!.?]*\s*$", re.I),
            re.compile(r"^\s*good\s+(morning|afternoon|evening|night)\s*[!.?]*\s*$", re.I),
        ],
    },
    "FAREWELL": {
        "stage1": "Conversation",
        "patterns": [
            re.compile(r"^\s*(bye|goodbye|see\s+you|take\s+care|later|cya|farewell)\s*[!.?]*\s*$", re.I),
        ],
    },
    "THANKS": {
        "stage1": "Conversation",
        "patterns": [
            re.compile(r"^\s*(thanks?|thank\s+you|thx|ty|appreciate|cheers)\s*[!.?]*\s*$", re.I),
        ],
    },
    "HELP": {
        "stage1": "Conversation",
        "patterns": [
            re.compile(r"^\s*help\s*[!.?]*\s*$", re.I),
            re.compile(r"what\s+can\s+you\s+do", re.I),
            re.compile(r"how\s+do\s+(i|we)\b", re.I),
        ],
    },
    "SMALL_TALK": {
        "stage1": "Conversation",
        "patterns": [
            re.compile(r"how\s+are\s+you", re.I),
            re.compile(r"what.s\s+up", re.I),
            re.compile(r"^\s*(ok|okay|sure|fine|cool|great|awesome|nice|wonderful|interesting)\s*[!.?]*\s*$", re.I),
        ],
    },
    # --- Expense ---
    "RECEIPT_UPLOAD": {
        "stage1": "Expense",
        "patterns": [
            re.compile(r"upload.{0,10}receipt", re.I),
            re.compile(r"attach.{0,10}receipt", re.I),
            re.compile(r"here.{0,5}(is|are)?.{0,5}(the|my)?\s*receipt", re.I),
            re.compile(r"receipt\s+(image|photo|scan|attached)", re.I),
            re.compile(r"submit.{0,10}receipt", re.I),
        ],
    },
    "AUDIT": {
        "stage1": "Expense",
        "patterns": [
            re.compile(r"\baudit\b", re.I),
            re.compile(r"review.{0,10}expense", re.I),
            re.compile(r"analyze.{0,10}expense", re.I),
            re.compile(r"check.{0,10}expense", re.I),
            re.compile(r"expense\s+(report|audit|review)", re.I),
        ],
    },
    "VALIDATION": {
        "stage1": "Expense",
        "patterns": [
            re.compile(r"\bvalidate\b", re.I),
            re.compile(r"\bverify\b.{0,10}(expense|receipt)?", re.I),
            re.compile(r"is\s+(this|it)\s+valid", re.I),
        ],
    },
    "FRAUD": {
        "stage1": "Expense",
        "patterns": [
            re.compile(r"\bfraud\b", re.I),
            re.compile(r"\bsuspicious\b", re.I),
            re.compile(r"fake\s+receipt", re.I),
            re.compile(r"duplicate\s+receipt", re.I),
            re.compile(r"\b(manipulated|forged|tampered|fraudulent)\b", re.I),
        ],
    },
    "REPORT": {
        "stage1": "Expense",
        "patterns": [
            re.compile(r"generate.{0,10}report", re.I),
            re.compile(r"create.{0,10}report", re.I),
            re.compile(r"(csv|markdown|pdf)\s+report", re.I),
        ],
    },
    # --- Question ---
    "POLICY": {
        "stage1": "Question",
        "patterns": [
            re.compile(r"(company|expense|travel|reimbursement|meal|hotel)\s+policy", re.I),
            re.compile(r"what\s+is\s+the\s+(limit|policy|rule)", re.I),
            re.compile(r"(spending|meal|hotel|travel)\s+limit", re.I),
            re.compile(r"\bpolicy\b", re.I),
        ],
    },
    "FINANCIAL": {
        "stage1": "Question",
        "patterns": [
            re.compile(r"\bcalculate\b", re.I),
            re.compile(r"how\s+much", re.I),
            re.compile(r"total.{0,10}expense", re.I),
            re.compile(r"reimbursement\s+amount", re.I),
        ],
    },
    "GENERAL_KNOWLEDGE": {
        "stage1": "Question",
        "patterns": [
            re.compile(r"^what\s+is\s+a?\s*\w+\s*\??$", re.I),
            re.compile(r"^who\s+is\b", re.I),
            re.compile(r"^define\s+", re.I),
        ],
    },
    # --- Command ---
    "CONTINUE": {
        "stage1": "Command",
        "patterns": [
            re.compile(r"^\s*(yes|yep|yeah|yup|correct|right|continue|go\s+ahead|proceed|carry\s+on)\s*[!.?]*\s*$", re.I),
        ],
    },
    "FOLLOW_UP": {
        "stage1": "Command",
        "patterns": [
            re.compile(r"why\s+did\s+(it|that)", re.I),
            re.compile(r"tell\s+me\s+more", re.I),
            re.compile(r"explain.{0,10}(why|that|this)", re.I),
            re.compile(r"what\s+about", re.I),
        ],
    },
    "RESTART": {
        "stage1": "Command",
        "patterns": [
            re.compile(r"\b(restart|start\s+over|reset|begin\s+again)\b", re.I),
        ],
    },
    "CANCEL": {
        "stage1": "Command",
        "patterns": [
            re.compile(r"\b(cancel|stop|abort|never\s+mind|forget\s+it)\b", re.I),
        ],
    },
}


class RegexClassifier(BaseIntentClassifier):
    """Regex-based classifier — good for structured patterns."""

    @property
    def name(self) -> str:
        return "regex"

    @property
    def weight(self) -> float:
        return 1.2  # slightly higher weight — regex is precise

    def classify(self, text: str, **context) -> ClassifierVote:
        text_stripped = text.strip()
        if not text_stripped:
            return ClassifierVote(self.name, "Unknown", "UNKNOWN", 0.0, "Empty input", (), ())

        best_intent = "UNKNOWN"
        best_stage1 = "Unknown"
        best_score = 0.0
        best_matched = []
        all_rejected = []

        for intent_name, definition in _PATTERNS.items():
            hits = [p.pattern for p in definition["patterns"] if p.search(text_stripped)]
            if hits:
                score = min(0.55 + 0.15 * len(hits), 1.0)
                if score > best_score:
                    best_score = score
                    best_intent = intent_name
                    best_stage1 = definition["stage1"]
                    best_matched = hits
            else:
                all_rejected.append(intent_name)

        reason = f"Regex matches: {len(best_matched)} patterns" if best_matched else "No regex matches"
        return ClassifierVote(
            self.name, best_stage1, best_intent, round(best_score, 3),
            reason, tuple(best_matched), tuple(all_rejected),
        )
