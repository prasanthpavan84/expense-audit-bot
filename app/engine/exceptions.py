"""Structured exceptions for the cognitive pipeline.

These replace raw ``assert`` statements with explicit, typed exceptions
that carry diagnostic context.
"""


class CognitiveError(Exception):
    """Base class for all cognitive pipeline errors."""

    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}


class ConversationFirewallViolation(CognitiveError):
    """Raised when a conversational intent attempts to execute an expense workflow."""
    pass


class WorkflowAuthorizationError(CognitiveError):
    """Raised when a workflow is executed without a valid ExecutionAuthorization."""
    pass


class PlannerValidationError(CognitiveError):
    """Raised when the planner produces an invalid or inconsistent plan."""
    pass


class InvalidLifecycleTransition(CognitiveError):
    """Raised when an invalid lifecycle state transition is attempted."""
    pass


class IntentClassificationError(CognitiveError):
    """Raised when intent classification produces an unrecoverable error."""
    pass


class ClarificationLoopError(CognitiveError):
    """Raised when clarification exceeds the maximum number of rounds."""
    pass


class ContextExpiredError(CognitiveError):
    """Raised when a conversation context has expired."""
    pass
