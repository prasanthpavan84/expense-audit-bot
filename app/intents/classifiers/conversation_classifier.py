"""Conversation Classifier — specialises in detecting conversational inputs.

This classifier has very high accuracy on greetings, farewells, thanks,
help, and small talk.  It is deliberately simple and conservative.
"""

import re
from app.intents.classifiers.base import BaseIntentClassifier, ClassifierVote

# Standalone conversational patterns — each is an exact-match on the
# full (stripped) input so we never accidentally match partial text.
_CONVERSATION_PATTERNS = {
    "GREETING": re.compile(
        r"^\s*(hi|hello|hey|howdy|hola|greetings|namaste|yo"
        r"|good\s*(morning|afternoon|evening|night))"
        r"\s*[!.?,;]*\s*$", re.I,
    ),
    "FAREWELL": re.compile(
        r"^\s*(bye|goodbye|see\s+you|take\s+care|later|cya|farewell|good\s*night)"
        r"\s*[!.?,;]*\s*$", re.I,
    ),
    "THANKS": re.compile(
        r"^\s*(thanks?|thank\s+you|thx|ty|appreciate\s+it|cheers|much\s+appreciated)"
        r"\s*[!.?,;]*\s*$", re.I,
    ),
    "HELP": re.compile(
        r"^\s*(help|help\s+me|what\s+can\s+you\s+do|how\s+does\s+this\s+work)"
        r"\s*[!.?]*\s*$", re.I,
    ),
    "SMALL_TALK": re.compile(
        r"^\s*(how\s+are\s+you|what.s\s+up|how.s\s+it\s+going"
        r"|ok|okay|sure|fine|cool|great|awesome|nice|wonderful|interesting"
        r"|no|nope|nah)"
        r"\s*[!.?,;]*\s*$", re.I,
    ),
}

# If ANY of these expense-related words appear, this classifier abstains
# so that it never accidentally mask a real expense request.
_EXPENSE_KEYWORDS = re.compile(
    r"\b(audit|receipt|expense|reimburse|invoice|fraud|validate|verify"
    r"|policy|report|calculate|total|amount|merchant|upload)\b", re.I,
)


class ConversationClassifier(BaseIntentClassifier):
    """Detects conversational inputs — abstains when expense keywords are present."""

    @property
    def name(self) -> str:
        return "conversation"

    @property
    def weight(self) -> float:
        return 1.3  # high weight — this classifier is very reliable

    def classify(self, text: str, **context) -> ClassifierVote:
        stripped = text.strip()
        if not stripped:
            return ClassifierVote(self.name, "Unknown", "UNKNOWN", 0.0, "Empty input", (), ())

        # If expense keywords are present alongside conversation words,
        # abstain — let the expense classifiers handle it.
        has_expense = bool(_EXPENSE_KEYWORDS.search(stripped))

        for intent_name, pattern in _CONVERSATION_PATTERNS.items():
            if pattern.fullmatch(stripped):
                if has_expense:
                    # Conversation pattern matches but expense keywords are also present.
                    # Abstain with low confidence.
                    return ClassifierVote(
                        self.name, "Conversation", intent_name, 0.30,
                        "Conversation pattern matched but expense keywords also present — abstaining",
                        (intent_name,), (),
                    )
                return ClassifierVote(
                    self.name, "Conversation", intent_name, 0.95,
                    f"Standalone conversational input matched: {intent_name}",
                    (intent_name,), (),
                )

        # Not a standalone conversational input
        return ClassifierVote(
            self.name, "Unknown", "UNKNOWN", 0.0,
            "Input does not match conversational patterns",
            (), tuple(_CONVERSATION_PATTERNS.keys()),
        )
