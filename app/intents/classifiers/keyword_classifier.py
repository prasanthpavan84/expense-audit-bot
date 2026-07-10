"""Keyword Classifier — matches exact keywords/phrases per intent.

This is the simplest classifier in the ensemble.
"""

from app.intents.classifiers.base import BaseIntentClassifier, ClassifierVote

# Stage 1 → Stage 2 keyword maps
_KEYWORDS = {
    # --- Conversation ---
    "Greeting": {
        "stage1": "Conversation",
        "keywords": [
            "hello",
            "hi",
            "hey",
            "howdy",
            "hola",
            "greetings",
            "namaste",
            "good morning",
            "good afternoon",
            "good evening",
            "good night",
            "yo",
        ],
    },
    "Farewell": {
        "stage1": "Conversation",
        "keywords": [
            "bye",
            "goodbye",
            "see you",
            "take care",
            "later",
            "cya",
            "farewell",
            "good night",
            "goodnight",
        ],
    },
    "Thanks": {
        "stage1": "Conversation",
        "keywords": [
            "thanks",
            "thank you",
            "thx",
            "ty",
            "appreciate it",
            "you're welcome",
            "cheers",
            "much appreciated",
        ],
    },
    "Help": {
        "stage1": "Conversation",
        "keywords": [
            "help",
            "assist",
            "support",
            "what can you do",
            "instructions",
            "how do i",
            "guide",
            "tutorial",
            "how does this work",
        ],
    },
    "Small_Talk": {
        "stage1": "Conversation",
        "keywords": [
            "how are you",
            "what's up",
            "how's it going",
            "nice day",
            "weather",
            "cool",
            "great",
            "awesome",
            "ok",
            "okay",
            "sure",
            "fine",
            "nice",
            "wonderful",
            "interesting",
        ],
    },
    # --- Expense ---
    "Receipt_Upload": {
        "stage1": "Expense",
        "keywords": [
            "upload receipt",
            "attach receipt",
            "here is the receipt",
            "receipt image",
            "scan receipt",
            "photo of receipt",
            "here's my receipt",
            "submit receipt",
            "receipt attached",
        ],
    },
    "Audit": {
        "stage1": "Expense",
        "keywords": [
            "audit",
            "review expense",
            "check expense",
            "expense report",
            "analyze expense",
            "audit expense",
            "please audit",
            "audit this",
            "expense audit",
            "audit my",
            "run audit",
        ],
    },
    "Validation": {
        "stage1": "Expense",
        "keywords": [
            "validate",
            "verify",
            "check validity",
            "is this valid",
            "correct format",
            "verify expense",
        ],
    },
    "Fraud": {
        "stage1": "Expense",
        "keywords": [
            "fraud",
            "suspicious",
            "fake receipt",
            "duplicate receipt",
            "manipulated",
            "forged",
            "tampered",
            "fraudulent",
        ],
    },
    "Report": {
        "stage1": "Expense",
        "keywords": [
            "report",
            "generate report",
            "summary",
            "csv report",
            "markdown report",
            "export",
            "create report",
        ],
    },
    # --- Question ---
    "Policy": {
        "stage1": "Question",
        "keywords": [
            "policy",
            "company policy",
            "expense policy",
            "limit",
            "what is the limit",
            "spending limit",
            "rules",
            "reimbursement policy",
            "travel policy",
            "meal limit",
            "hotel limit",
            "allowed",
            "permitted",
        ],
    },
    "Financial": {
        "stage1": "Question",
        "keywords": [
            "calculate",
            "total",
            "sum",
            "reimbursable",
            "how much",
            "cost",
            "spending",
            "budget",
            "reimbursement amount",
        ],
    },
    "General_Knowledge": {
        "stage1": "Question",
        "keywords": [
            "what is",
            "who is",
            "define",
            "meaning of",
            "definition",
            "explain concept",
        ],
    },
    # --- Command ---
    "Continue": {
        "stage1": "Command",
        "keywords": [
            "continue",
            "next",
            "go ahead",
            "proceed",
            "carry on",
            "yes",
            "yep",
            "yeah",
            "yup",
            "correct",
            "right",
        ],
    },
    "Follow_Up": {
        "stage1": "Command",
        "keywords": [
            "why",
            "explain",
            "tell me more",
            "what happened",
            "reason",
            "elaborate",
            "details",
            "clarify",
            "also",
            "and also",
            "additionally",
            "what about",
            "another",
        ],
    },
    "Restart": {
        "stage1": "Command",
        "keywords": ["restart", "start over", "reset", "begin again", "new conversation"],
    },
    "Cancel": {
        "stage1": "Command",
        "keywords": ["cancel", "stop", "abort", "never mind", "forget it"],
    },
}


class KeywordClassifier(BaseIntentClassifier):
    """Matches exact keywords/phrases."""

    @property
    def name(self) -> str:
        return "keyword"

    @property
    def weight(self) -> float:
        return 1.0

    def classify(self, text: str, **context) -> ClassifierVote:
        text_lower = text.lower().strip()
        if not text_lower:
            return ClassifierVote(self.name, "Unknown", "UNKNOWN", 0.0, "Empty input", (), ())

        best_intent = "UNKNOWN"
        best_stage1 = "Unknown"
        best_score = 0.0
        best_matched = []
        all_rejected = []

        import re

        for intent_name, definition in _KEYWORDS.items():
            matched_kws = []
            for kw in definition["keywords"]:
                # Use word boundaries to prevent substring matches (e.g. "hi" in "Hilton")
                # re.escape is used in case keywords contain special chars
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, text_lower):
                    matched_kws.append(kw)

            if matched_kws:
                # Score: more matches = higher confidence
                score = min(0.50 + 0.15 * len(matched_kws), 1.0)
                # Exact match bonus: if the entire input is a keyword
                if text_lower in definition["keywords"]:
                    score = min(score + 0.25, 1.0)
                if score > best_score:
                    best_score = score
                    best_intent = intent_name.upper()
                    best_stage1 = definition["stage1"]
                    best_matched = matched_kws
            else:
                all_rejected.append(intent_name.upper())

        reason = f"Matched keywords: {best_matched}" if best_matched else "No keyword matches"
        return ClassifierVote(
            self.name,
            best_stage1,
            best_intent,
            round(best_score, 3),
            reason,
            tuple(best_matched),
            tuple(all_rejected),
        )
