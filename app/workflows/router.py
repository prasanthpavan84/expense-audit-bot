"""Intent Router Agent — v2 (Hardened).

Runs the full intent classification pipeline and stores the immutable
``IntentDecision`` in state metadata.  Backward compatible with legacy
intent format.
"""

import json
from pathlib import Path

from app.core.agent_base import BaseExpenseAgent
from app.intents.intent_engine import IntentEngine
from app.intents.nlu import NLU
from app.models.state import WorkflowState

# Load intent taxonomy once at module load
_TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "intents" / "intent_taxonomy.json"
with open(_TAXONOMY_PATH, encoding="utf-8") as f:
    INTENT_TAXONOMY = json.load(f)


class IntentRouterAgent(BaseExpenseAgent):
    """Agent responsible for classifying user intent(s) and updating the state.

    Uses the hardened IntentEngine with ensemble classification.
    """

    def __init__(self):
        super().__init__(name="intent_router", system_instruction="Classify the user intent(s)")

    async def process_state(self, state: WorkflowState) -> WorkflowState:
        """Analyzes the raw input and determines one or more workflow intents."""
        # Run NLU extraction first
        nlu_result = NLU.extract_entities(state.raw_input)
        state.metadata["nlu_entities"] = nlu_result.entities
        state.metadata["conversation_context"] = {
            "context_type": nlu_result.context_type,
            "confidence": nlu_result.confidence,
        }
        if nlu_result.user_role:
            state.metadata["user_role"] = nlu_result.user_role

        # Full intent classification (hierarchical, ensemble-based)
        intent_decision = IntentEngine.classify_full(state.raw_input)
        state.metadata["intent_decision"] = intent_decision

        # Backward-compatible IntentResult
        intent_result = IntentEngine.classify(state.raw_input)
        state.metadata["intent_result"] = intent_result
        state.metadata["intent_confidence"] = intent_result.confidence
        state.metadata["intent_reason"] = intent_result.reason

        # Map to legacy workflow intent
        legacy_intent = IntentEngine.map_to_workflow_intent(intent_decision.stage2_intent)
        state.intent = legacy_intent

        # Build legacy intents list
        secondary = None
        if intent_result.secondary_intents:
            top_sec = intent_result.secondary_intents[0]["intent"]
            secondary = IntentEngine.map_to_workflow_intent(top_sec)
            if secondary == legacy_intent:
                secondary = None

        intents = [{"primary": legacy_intent, "secondary": secondary, "confidence": intent_result.confidence}]
        state.metadata["intents"] = intents

        # Primary/secondary intent fields for existing code paths
        state.metadata["primary_intent"] = legacy_intent
        state.metadata["secondary_intent"] = secondary

        # Classify critical/optional fields based on legacy mapped intent
        NLU.classify_missing_fields(nlu_result, legacy_intent)
        state.metadata["missing_critical"] = nlu_result.missing_critical
        state.metadata["missing_optional"] = nlu_result.missing_optional

        return state
