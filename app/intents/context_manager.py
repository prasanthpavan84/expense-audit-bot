"""Conversation Context Manager — v2 (Hardened).

Maintains in-memory conversation state with:
  - Intent stability (tiny replies inherit pending intent)
  - Stale state isolation (new conversations clear old workflow data)
  - Context expiration (timeout, restart, cancel)
  - Lifecycle state machine
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.state import WorkflowState

# Valid conversation lifecycle states
LIFECYCLE_STATES = {"STARTED", "ACTIVE", "CLARIFYING", "COMPLETING", "ENDED"}

# Valid state transition matrix
LIFECYCLE_TRANSITIONS = {
    "STARTED": ["ACTIVE", "CLARIFYING"],
    "ACTIVE": ["CLARIFYING", "COMPLETING", "ENDED"],
    "CLARIFYING": ["ACTIVE", "COMPLETING", "ENDED"],
    "COMPLETING": ["ENDED"],
    "ENDED": ["STARTED", "ACTIVE"],
}

# Context expiration timeout (seconds)
CONTEXT_TIMEOUT_SECONDS = 20 * 60  # 20 minutes


@dataclass
class ConversationContext:
    """Dataclass holding context state."""
    previous_intent: Optional[str] = None
    current_workflow: Optional[str] = None
    active_receipt: Optional[Dict[str, Any]] = None
    active_report: Optional[Dict[str, Any]] = None
    clarification_history: List[str] = field(default_factory=list)
    conversation_turns: List[Dict[str, Any]] = field(default_factory=list)
    follow_up_refs: Dict[str, Any] = field(default_factory=dict)
    lifecycle_state: str = "STARTED"
    pending_clarification_intent: Optional[str] = None
    last_activity_timestamp: float = field(default_factory=time.time)


class ContextManager:
    """Manages in-memory conversation context, lifecycle, and intent stability."""

    @staticmethod
    def get_or_create_context(state: WorkflowState) -> ConversationContext:
        """Retrieves context from state metadata or creates a new one."""
        if "context" not in state.metadata:
            ctx = ConversationContext()
            state.metadata["context"] = ctx.__dict__
            return ctx

        ctx_dict = state.metadata["context"]
        if isinstance(ctx_dict, ConversationContext):
            return ctx_dict

        return ConversationContext(
            previous_intent=ctx_dict.get("previous_intent"),
            current_workflow=ctx_dict.get("current_workflow"),
            active_receipt=ctx_dict.get("active_receipt"),
            active_report=ctx_dict.get("active_report"),
            clarification_history=ctx_dict.get("clarification_history", []),
            conversation_turns=ctx_dict.get("conversation_turns", []),
            follow_up_refs=ctx_dict.get("follow_up_refs", {}),
            lifecycle_state=ctx_dict.get("lifecycle_state", "STARTED"),
            pending_clarification_intent=ctx_dict.get("pending_clarification_intent"),
            last_activity_timestamp=ctx_dict.get("last_activity_timestamp", time.time()),
        )

    @staticmethod
    def save_context(state: WorkflowState, context: ConversationContext) -> None:
        """Saves the context back into state metadata as a dict."""
        state.metadata["context"] = {
            "previous_intent": context.previous_intent,
            "current_workflow": context.current_workflow,
            "active_receipt": context.active_receipt,
            "active_report": context.active_report,
            "clarification_history": context.clarification_history,
            "conversation_turns": context.conversation_turns,
            "follow_up_refs": context.follow_up_refs,
            "lifecycle_state": context.lifecycle_state,
            "pending_clarification_intent": context.pending_clarification_intent,
            "last_activity_timestamp": context.last_activity_timestamp,
        }

    @classmethod
    def update(cls, state: WorkflowState) -> WorkflowState:
        """Updates context with the current turn information."""
        context = cls.get_or_create_context(state)

        # Check expiration
        if cls._is_expired(context):
            cls._reset_context(context)

        # Update activity timestamp
        context.last_activity_timestamp = time.time()

        # Record this turn
        turn = {
            "raw_input": state.raw_input,
            "intent": state.intent,
            "entities": state.metadata.get("nlu_entities", {}),
            "timestamp": state.metadata.get("timestamp"),
        }
        context.conversation_turns.append(turn)

        # Update previous intent if appropriate
        if state.intent and state.intent != "CONVERSATION":
            context.previous_intent = state.intent

        # Update active receipt reference if extraction was successful
        if "extraction_results" in state.metadata:
            context.active_receipt = state.metadata["extraction_results"]

        # Transition lifecycle
        next_lifecycle = "CLARIFYING" if state.metadata.get("needs_clarification") else "ACTIVE"
        current = context.lifecycle_state
        allowed = LIFECYCLE_TRANSITIONS.get(current, [])
        if next_lifecycle in allowed or next_lifecycle == current:
            context.lifecycle_state = next_lifecycle

        cls.save_context(state, context)
        return state

    @classmethod
    def transition_to(cls, state: WorkflowState, next_state: str) -> bool:
        """Transitions the conversation to the next lifecycle state."""
        if next_state not in LIFECYCLE_STATES:
            return False

        context = cls.get_or_create_context(state)
        current = context.lifecycle_state

        allowed = LIFECYCLE_TRANSITIONS.get(current, [])
        if next_state in allowed or next_state == current:
            context.lifecycle_state = next_state
            cls.save_context(state, context)
            return True
        return False

    @classmethod
    def resolve_follow_up(cls, state: WorkflowState) -> WorkflowState:
        """Checks if current input references a previous result and enriches context."""
        context = cls.get_or_create_context(state)
        text_lower = state.raw_input.lower()

        references_previous = any(
            phrase in text_lower
            for phrase in ["why did it", "explain that", "what about the last", "re-audit", "reason for"]
        )

        if references_previous and context.previous_intent:
            state.metadata["is_follow_up"] = True
            state.metadata["follow_up_intent"] = context.previous_intent
            if context.active_receipt:
                state.metadata["active_receipt_ref"] = context.active_receipt

        cls.save_context(state, context)
        return state

    @classmethod
    def get_pending_intent(cls, state: WorkflowState) -> Optional[str]:
        """Gets the intent that was pending when clarification started."""
        context = cls.get_or_create_context(state)
        return context.pending_clarification_intent

    @classmethod
    def set_pending_intent(cls, state: WorkflowState, intent: Optional[str]) -> None:
        """Sets the pending clarification intent in context."""
        context = cls.get_or_create_context(state)
        context.pending_clarification_intent = intent
        cls.save_context(state, context)

    @classmethod
    def clear_pending_intent(cls, state: WorkflowState) -> None:
        """Clears the pending clarification intent."""
        cls.set_pending_intent(state, None)

    @staticmethod
    def _is_expired(context: ConversationContext) -> bool:
        """Check if the context has expired due to inactivity."""
        elapsed = time.time() - context.last_activity_timestamp
        if elapsed > CONTEXT_TIMEOUT_SECONDS:
            return True
        if context.lifecycle_state == "ENDED":
            return True
        return False

    @staticmethod
    def _reset_context(context: ConversationContext) -> None:
        """Reset context to initial state."""
        context.previous_intent = None
        context.current_workflow = None
        context.active_receipt = None
        context.active_report = None
        context.clarification_history = []
        context.follow_up_refs = {}
        context.lifecycle_state = "STARTED"
        context.pending_clarification_intent = None
        context.last_activity_timestamp = time.time()
