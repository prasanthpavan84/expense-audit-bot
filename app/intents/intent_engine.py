"""Hardened Intent Classification Engine — v2.

Replaces the original intent_engine.py with:
  - Input normalization, input type detection, noise detection, receipt detection
  - Hierarchical Stage 1 / Stage 2 classification
  - Ensemble voting (Keyword, Regex, Conversation classifiers)
  - Negative matching and confidence breakdown
  - Dynamic per-intent confidence thresholds
  - Intent Lock for conversational intents
  - Full backward compatibility via ``map_to_workflow_intent()``

The original ``IntentResult`` class is preserved for backward compatibility.

Core principle: THE AI MUST NEVER GUESS.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.intents.classifiers.base import ClassifierVote
from app.intents.classifiers.conversation_classifier import ConversationClassifier
from app.intents.classifiers.keyword_classifier import KeywordClassifier
from app.intents.classifiers.regex_classifier import RegexClassifier
from app.intents.preprocessors.input_classifier import InputClassifier, InputType
from app.intents.preprocessors.input_normalizer import InputNormalizer
from app.intents.preprocessors.noise_detector import NoiseDetector
from app.intents.preprocessors.receipt_detector import ReceiptDetector

# ---------------------------------------------------------------------------
# Immutable Decision Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntentDecision:
    """Immutable, single source of truth for intent classification."""

    decision_id: str
    raw_input: str
    normalized_input: str
    input_type: str
    stage1_category: str
    stage2_intent: str
    confidence: float
    confidence_breakdown: dict[str, float]
    classifier_votes: tuple[ClassifierVote, ...]
    negative_matches: tuple[str, ...]
    reason: str
    requires_clarification: bool
    planner_permission: bool
    timestamp: str


# Backward-compat wrapper — existing code expects IntentResult
@dataclass
class IntentResult:
    """Result of intent classification — backward compatible."""

    intent: str
    confidence: float
    reason: str
    secondary_intents: list[dict[str, float]] = field(default_factory=list)
    is_ambiguous: bool = False


# ---------------------------------------------------------------------------
# Taxonomy & Thresholds
# ---------------------------------------------------------------------------

# The canonical Stage 1 → Stage 2 taxonomy.
INTENT_TAXONOMY: dict[str, list[str]] = {
    "Conversation": ["GREETING", "FAREWELL", "THANKS", "HELP", "SMALL_TALK"],
    "Expense": ["RECEIPT_UPLOAD", "AUDIT", "VALIDATION", "FRAUD", "REPORT"],
    "Question": ["POLICY", "FINANCIAL", "GENERAL_KNOWLEDGE"],
    "Command": ["CONTINUE", "FOLLOW_UP", "RESTART", "CANCEL"],
    "Unknown": ["UNKNOWN"],
}

# Intents that belong to conversation (never trigger expense workflows)
CONVERSATION_INTENTS: frozenset[str] = frozenset(
    {
        "GREETING",
        "FAREWELL",
        "THANKS",
        "HELP",
        "SMALL_TALK",
        "GENERAL_KNOWLEDGE",
        "UNKNOWN",
    }
)

# Non-expense intents (conversation + commands that don't directly trigger workflows)
NON_EXPENSE_INTENTS: frozenset[str] = CONVERSATION_INTENTS | frozenset(
    {
        "CONTINUE",
        "FOLLOW_UP",
        "RESTART",
        "CANCEL",
    }
)

# Per-intent confidence thresholds — high-risk intents need higher confidence
INTENT_CONFIDENCE_THRESHOLDS: dict[str, float] = {
    "FRAUD": 0.95,
    "AUDIT": 0.90,
    "RECEIPT_UPLOAD": 0.80,
    "VALIDATION": 0.85,
    "REPORT": 0.80,
    "POLICY": 0.85,
    "FINANCIAL": 0.80,
    "GREETING": 0.60,
    "FAREWELL": 0.60,
    "THANKS": 0.60,
    "HELP": 0.60,
    "SMALL_TALK": 0.55,
    "CONTINUE": 0.75,
    "FOLLOW_UP": 0.70,
    "GENERAL_KNOWLEDGE": 0.65,
    "RESTART": 0.70,
    "CANCEL": 0.70,
}

# Hard priority rules — when multiple intents compete, higher priority wins.
# Receipt/Expense > Question > Command > Conversation > Unknown
INTENT_PRIORITY: dict[str, int] = {
    "RECEIPT_UPLOAD": 100,
    "FRAUD": 95,
    "AUDIT": 90,
    "VALIDATION": 85,
    "REPORT": 80,
    "POLICY": 75,
    "FINANCIAL": 70,
    "FOLLOW_UP": 60,
    "CONTINUE": 55,
    "RESTART": 50,
    "CANCEL": 45,
    "HELP": 30,
    "GREETING": 20,
    "THANKS": 15,
    "SMALL_TALK": 10,
    "FAREWELL": 5,
    "GENERAL_KNOWLEDGE": 3,
    "UNKNOWN": 0,
}

# Mapping from granular intents to legacy workflow intents for backward compat
_WORKFLOW_INTENT_MAP: dict[str, str] = {
    "GREETING": "CONVERSATION",
    "FAREWELL": "CONVERSATION",
    "THANKS": "CONVERSATION",
    "HELP": "CONVERSATION",
    "SMALL_TALK": "CONVERSATION",
    "GENERAL_KNOWLEDGE": "CONVERSATION",
    "UNKNOWN": "CONVERSATION",  # UNKNOWN → CONVERSATION, never AUDIT
    "RECEIPT_UPLOAD": "EXTRACT",
    "AUDIT": "AUDIT",
    "VALIDATION": "AUDIT",
    "FRAUD": "AUDIT",
    "REPORT": "QUERY",
    "POLICY": "POLICY",
    "FINANCIAL": "CALCULATE",
    "FOLLOW_UP": "QUERY",
    "CONTINUE": "QUERY",
    "RESTART": "CONVERSATION",
    "CANCEL": "CONVERSATION",
}


# ---------------------------------------------------------------------------
# Ensemble Intent Engine
# ---------------------------------------------------------------------------


class IntentEngine:
    """Hardened, ensemble-based, hierarchical intent classifier.

    Pipeline:
      1. Normalize input
      2. Detect input type (NOISE, RECEIPT, CODE, etc.)
      3. Detect noise
      4. Detect receipt
      5. Run ensemble classifiers (Keyword, Regex, Conversation)
      6. Weighted vote → Stage 1 / Stage 2
      7. Apply hard priority rules
      8. Apply per-intent confidence threshold → clarification flag
      9. Intent Lock (conversational → never overridable)
     10. Produce immutable IntentDecision
    """

    # Singleton classifiers (stateless)
    _keyword_clf = KeywordClassifier()
    _regex_clf = RegexClassifier()
    _conversation_clf = ConversationClassifier()

    @classmethod
    def classify_full(cls, text: str, **context: Any) -> IntentDecision:
        """Full classification pipeline → immutable IntentDecision."""
        decision_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        # --- 1. Normalize ---
        norm = InputNormalizer.normalize(text)
        normalized = norm.normalized

        # --- 2. Input type ---
        input_type_result = InputClassifier.classify(normalized)
        input_type = input_type_result.input_type

        # --- 3. Noise detection ---
        noise = NoiseDetector.detect(normalized)

        # --- 4. Short-circuit: NOISE, EMPTY, PUNCTUATION, NUMBER ---
        if input_type in (InputType.EMPTY, InputType.WHITESPACE):
            return cls._make_decision(
                decision_id,
                text,
                normalized,
                input_type.value,
                "Unknown",
                "UNKNOWN",
                0.0,
                {},
                (),
                (),
                "Empty/whitespace input",
                requires_clarification=True,
                planner_permission=False,
                timestamp=timestamp,
            )

        if noise.is_noise or input_type in (InputType.NOISE, InputType.PUNCTUATION):
            return cls._make_decision(
                decision_id,
                text,
                normalized,
                input_type.value,
                "Unknown",
                "UNKNOWN",
                0.0,
                {},
                (),
                (),
                f"Noise detected: {noise.noise_type} — {noise.reason}",
                requires_clarification=True,
                planner_permission=False,
                timestamp=timestamp,
            )

        if input_type == InputType.NUMBER:
            return cls._make_decision(
                decision_id,
                text,
                normalized,
                input_type.value,
                "Unknown",
                "UNKNOWN",
                0.0,
                {},
                (),
                (),
                "Pure numeric input — not an expense request",
                requires_clarification=True,
                planner_permission=False,
                timestamp=timestamp,
            )

        if input_type in (InputType.CODE, InputType.JSON, InputType.MARKDOWN, InputType.TABLE, InputType.CSV):
            return cls._make_decision(
                decision_id,
                text,
                normalized,
                input_type.value,
                "Unknown",
                "UNKNOWN",
                0.0,
                {},
                (),
                (),
                f"Input type is {input_type.value} — not a natural language request",
                requires_clarification=True,
                planner_permission=False,
                timestamp=timestamp,
            )

        # --- 5. Receipt detection ---
        receipt = ReceiptDetector.detect(normalized)

        # --- 6. Run ensemble classifiers ---
        votes = [
            cls._keyword_clf.classify(normalized, **context),
            cls._regex_clf.classify(normalized, **context),
            cls._conversation_clf.classify(normalized, **context),
        ]

        # --- 7. Weighted voting ---
        intent_scores: dict[str, float] = {}
        intent_stage1: dict[str, str] = {}
        total_weight = 0.0

        for vote in votes:
            if vote.confidence > 0:
                w = cls._get_classifier_weight(vote.classifier_name)
                key = vote.stage2_intent
                intent_scores[key] = intent_scores.get(key, 0.0) + vote.confidence * w
                intent_stage1[key] = vote.stage1_category
                total_weight += w

        # Normalize scores
        if total_weight > 0:
            for k in intent_scores:
                intent_scores[k] = round(intent_scores[k] / total_weight, 3)

        # --- 8. Receipt boost ---
        if receipt.is_receipt and receipt.probability >= 0.4:
            # Boost expense intents
            for expense_intent in ("AUDIT", "RECEIPT_UPLOAD", "VALIDATION"):
                if expense_intent in intent_scores:
                    intent_scores[expense_intent] = min(intent_scores[expense_intent] + receipt.probability * 0.3, 1.0)
                else:
                    intent_scores[expense_intent] = receipt.probability * 0.5
                    intent_stage1[expense_intent] = "Expense"

        # --- 9. Pick winner with hard priority tie-breaking ---
        if not intent_scores:
            best_intent = "UNKNOWN"
            best_stage1 = "Unknown"
            best_confidence = 0.0
        else:
            # Sort by (score, priority) descending
            ranked = sorted(
                intent_scores.items(),
                key=lambda kv: (kv[1], INTENT_PRIORITY.get(kv[0], 0)),
                reverse=True,
            )
            best_intent = ranked[0][0]
            best_confidence = ranked[0][1]
            best_stage1 = intent_stage1.get(best_intent, "Unknown")

        # --- 10. Negative evidence ---
        all_negative = set()
        for vote in votes:
            all_negative.update(vote.negative_evidence)
        all_negative.discard(best_intent)

        # --- 11. Confidence breakdown ---
        confidence_breakdown = {vote.classifier_name: vote.confidence for vote in votes}
        confidence_breakdown["receipt"] = receipt.probability

        # --- 12. Intent Lock: conversational intents cannot be overridden ---
        is_conversation_locked = False
        # If the conversation classifier voted with high confidence, lock it
        conv_vote = votes[2]  # ConversationClassifier is always 3rd
        if conv_vote.confidence >= 0.80 and conv_vote.stage2_intent in CONVERSATION_INTENTS:
            # Only override if a *high-priority* expense intent beat it
            if best_intent not in CONVERSATION_INTENTS:
                expense_threshold = INTENT_CONFIDENCE_THRESHOLDS.get(best_intent, 0.80)
                if best_confidence < expense_threshold:
                    # Not enough evidence for expense → lock to conversation
                    best_intent = conv_vote.stage2_intent
                    best_stage1 = "Conversation"
                    best_confidence = conv_vote.confidence
                    is_conversation_locked = True

        # --- 13. Per-intent threshold → clarification ---
        threshold = INTENT_CONFIDENCE_THRESHOLDS.get(best_intent, 0.80)
        requires_clarification = best_confidence < threshold

        # Very low confidence → treat as UNKNOWN
        if best_confidence < 0.55:
            best_intent = "UNKNOWN"
            best_stage1 = "Unknown"
            requires_clarification = True

        # --- 14. Planner permission ---
        planner_permission = (
            not requires_clarification and best_intent not in CONVERSATION_INTENTS and best_confidence >= threshold
        )

        # --- 15. Build reason ---
        reason_parts = [f"Input type: {input_type.value}"]
        if receipt.is_receipt:
            reason_parts.append(f"Receipt detected (p={receipt.probability:.2f})")
        if is_conversation_locked:
            reason_parts.append("Intent locked to conversation (insufficient expense evidence)")
        reason_parts.append(f"Winner: {best_intent} (conf={best_confidence:.3f}, threshold={threshold:.2f})")
        reason = "; ".join(reason_parts)

        return cls._make_decision(
            decision_id,
            text,
            normalized,
            input_type.value,
            best_stage1,
            best_intent,
            best_confidence,
            confidence_breakdown,
            tuple(votes),
            tuple(sorted(all_negative)),
            reason,
            requires_clarification,
            planner_permission,
            timestamp,
        )

    @classmethod
    def classify(cls, text: str) -> IntentResult:
        """Backward-compatible wrapper that returns ``IntentResult``.

        Existing code paths (router, orchestrator) call this method.
        """
        decision = cls.classify_full(text)

        # Map stage2 intent to the old intent names for backward compat
        old_intent = decision.stage2_intent
        # Map some renamed intents back
        _back_compat = {
            "THANKS": "SMALL_TALK",
            "CONTINUE": "CONTINUATION",
            "FOLLOW_UP": "FOLLOW_UP",
        }
        old_intent = _back_compat.get(old_intent, old_intent)

        return IntentResult(
            intent=old_intent,
            confidence=decision.confidence,
            reason=decision.reason,
            secondary_intents=[],
            is_ambiguous=decision.requires_clarification and decision.confidence >= 0.55,
        )

    @staticmethod
    def map_to_workflow_intent(intent: str) -> str:
        """Map a granular intent to a legacy workflow intent string.

        Returns one of: AUDIT, POLICY, QUERY, CALCULATE, EXTRACT, CONVERSATION.
        NEVER defaults to AUDIT — unknown maps to CONVERSATION.
        """
        return _WORKFLOW_INTENT_MAP.get(intent, "CONVERSATION")

    @staticmethod
    def is_conversation_intent(intent: str) -> bool:
        """Check if the intent is conversational (should never trigger expense workflows)."""
        return intent in CONVERSATION_INTENTS

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    @classmethod
    def _get_classifier_weight(cls, name: str) -> float:
        """Return the weight of a classifier by name."""
        weights = {
            "keyword": cls._keyword_clf.weight,
            "regex": cls._regex_clf.weight,
            "conversation": cls._conversation_clf.weight,
        }
        return weights.get(name, 1.0)

    @staticmethod
    def _make_decision(
        decision_id: str,
        raw_input: str,
        normalized_input: str,
        input_type: str,
        stage1: str,
        stage2: str,
        confidence: float,
        breakdown: dict[str, float],
        votes: tuple,
        negative: tuple,
        reason: str,
        requires_clarification: bool,
        planner_permission: bool,
        timestamp: str,
    ) -> IntentDecision:
        return IntentDecision(
            decision_id=decision_id,
            raw_input=raw_input,
            normalized_input=normalized_input,
            input_type=input_type,
            stage1_category=stage1,
            stage2_intent=stage2,
            confidence=round(confidence, 3),
            confidence_breakdown=breakdown,
            classifier_votes=votes,
            negative_matches=negative,
            reason=reason,
            requires_clarification=requires_clarification,
            planner_permission=planner_permission,
            timestamp=timestamp,
        )
