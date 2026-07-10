"""Multi-Intent Detection and Priority Ranking.

Detects multiple user intents from a single input string and ranks them
according to security and business priority.
"""

from app.intents.intent_engine import IntentEngine, IntentResult

# Priority order: Security (FRAUD) > Audit (AUDIT) > Policy (POLICY) > Query (QUERY/FINANCIAL/REPORT/FOLLOW_UP) > Conversation
INTENT_PRIORITY = {
    "FRAUD": 100,
    "AUDIT": 90,
    "RECEIPT_UPLOAD": 85,
    "POLICY": 80,
    "REPORT": 70,
    "FINANCIAL": 65,
    "VALIDATION": 60,
    "FOLLOW_UP": 50,
    "CONTINUATION": 40,
    "HELP": 30,
    "GREETING": 20,
    "SMALL_TALK": 10,
    "FAREWELL": 5,
    "GENERAL_KNOWLEDGE": 2,
    "UNSUPPORTED": 0,
}


def get_priority(intent: str) -> int:
    """Returns the priority value for an intent name."""
    return INTENT_PRIORITY.get(intent, 0)


class MultiIntentDetector:
    """Detects and ranks multiple intents from a single user message."""

    @staticmethod
    def detect_all_intents(text: str) -> list[IntentResult]:
        """Runs the classifier to detect all intents matching the input text,

        returning them ranked by a combination of confidence and priority.
        """
        if not text or not text.strip():
            return []

        # Split text by punctuation or conjunctions to detect sub-clauses
        clauses = [c.strip() for c in re_split_clauses(text) if c.strip()]
        if len(clauses) <= 1:
            # Try to match multiple patterns in the single string
            results = []
            primary_res = IntentEngine.classify(text)
            results.append(primary_res)

            # Extract secondary intents matching from engine results
            for sec in primary_res.secondary_intents:
                sec_name = sec["intent"]
                sec_conf = sec["confidence"]
                if sec_conf >= 0.4:  # minimum confidence threshold
                    results.append(
                        IntentResult(
                            intent=sec_name,
                            confidence=sec_conf,
                            reason=f"Detected as secondary intent of input: {text}",
                            is_ambiguous=False,
                        )
                    )
        else:
            results = []
            for clause in clauses:
                res = IntentEngine.classify(clause)
                if res.confidence >= 0.4 and not any(r.intent == res.intent for r in results):
                    results.append(res)

            # If nothing found in sub-clauses, fall back to classification on full text
            if not results:
                results.append(IntentEngine.classify(text))

        # Rank results by business priority * confidence score
        results.sort(key=lambda x: get_priority(x.intent) * x.confidence, reverse=True)
        return results


def re_split_clauses(text: str) -> list[str]:
    """Helper to split user input into logical clauses by conjunctions or punctuation."""
    import re

    # Split by: and, but, then, also, as well as, punctuation
    delimiters = r"\band\b|\bbut\b|\bthen\b|\balso\b|[,;\.\?!]"
    return re.split(delimiters, text, flags=re.IGNORECASE)
