"""Clarification Manager for the AI Cognitive Layer.

Determines if clarification is required, generates contextual questions,
and prevents infinite loops or invalid lifecycle state jumps.
"""

from typing import Dict, Any, List
from app.models.state import WorkflowState
from app.intents.context_manager import ContextManager

MAX_CLARIFICATION_ROUNDS = 3


class ClarificationManager:
    """Manages clarification requests, session retries, and transition validation."""

    @staticmethod
    def get_or_create_session(state: WorkflowState) -> Dict[str, Any]:
        """Retrieves or initializes the clarification session in state metadata."""
        if "clarification_session" not in state.metadata:
            state.metadata["clarification_session"] = {
                "missing_fields": [],
                "requested_fields": [],
                "resolved_fields": [],
                "retry_count": 0,
                "max_retries": MAX_CLARIFICATION_ROUNDS
            }
        return state.metadata["clarification_session"]

    @classmethod
    def should_clarify(cls, state: WorkflowState) -> bool:
        """Determines if the current execution requires clarification."""
        # 1. Ambiguous intent
        intent_res = state.metadata.get("intent_result")
        if intent_res and intent_res.is_ambiguous:
            return True

        # 2. Critical fields missing
        missing_crit = state.metadata.get("missing_critical", [])
        if missing_crit:
            return True

        # 3. Overall confidence below threshold (default 0.6)
        calibrated_conf = state.metadata.get("calibrated_confidence", 1.0)
        if calibrated_conf < 0.6:
            return True

        return False

    @classmethod
    def generate_question(cls, state: WorkflowState) -> str:
        """Generates a helpful, contextual clarification question."""
        session = cls.get_or_create_session(state)
        
        # Guard: Recursive loop prevention
        if session.get("retry_count", 0) >= MAX_CLARIFICATION_ROUNDS:
            return "I wasn't able to gather enough information after multiple attempts. Please provide the complete details and try again."

        # Increment retry count
        session["retry_count"] = session.get("retry_count", 0) + 1

        # Determine what's missing
        missing_crit = state.metadata.get("missing_critical", [])
        intent_res = state.metadata.get("intent_result")

        # 1. Ambiguous intent
        if intent_res and intent_res.is_ambiguous:
            question = (
                f"I'm not sure if you want to {intent_res.intent} or something else. "
                "Could you please specify your goal?"
            )
            session["requested_fields"].append("intent_clarification")
            return question

        # 2. Missing critical fields
        if missing_crit:
            fields_str = ", ".join(missing_crit)
            question = f"I found some information, but I'm missing critical fields: {fields_str}. Could you please provide them?"
            session["requested_fields"].extend(missing_crit)
            session["missing_fields"] = list(set(session.get("missing_fields", []) + missing_crit))
            return question

        # 3. Low overall confidence
        calibrated_conf = state.metadata.get("calibrated_confidence", 1.0)
        if calibrated_conf < 0.6:
            question = "I'm not confident about the extracted information. Could you please double-check the receipt details?"
            session["requested_fields"].append("general_verification")
            return question

        return "Could you please provide more details about your request?"

    @classmethod
    def check_resolved(cls, state: WorkflowState) -> bool:
        """Compares current NLU entities against missing fields from the session.

        If all previously critical missing fields are now present, returns True.
        """
        session = cls.get_or_create_session(state)
        missing = session.get("missing_fields", [])
        if not missing:
            return True

        nlu_entities = state.metadata.get("nlu_entities", {})
        
        # Check if all fields in 'missing' are now present in extracted entities
        resolved = []
        for field_name in missing:
            if field_name in nlu_entities:
                resolved.append(field_name)

        if resolved:
            # Update lists
            session["resolved_fields"] = list(set(session.get("resolved_fields", []) + resolved))
            session["missing_fields"] = [f for f in missing if f not in resolved]
            
        # Resolved if no critical fields are left missing
        return len(session["missing_fields"]) == 0
