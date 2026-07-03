# framework/runtime/runtime_state.py
"""Defines the runtime states and a finite state machine for transitions.

The FSM validates each transition and raises :class:`InvalidStateTransitionError`
if an illegal move is attempted.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Set, Dict


class RuntimeState(Enum):
    """All possible states of the runtime lifecycle."""

    CREATED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    WAITING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    SHUTDOWN = auto()

    def __str__(self) -> str:
        return self.name


# Mapping of allowed transitions: current -> {allowed next states}
_ALLOWED_TRANSITIONS: Dict[RuntimeState, Set[RuntimeState]] = {
    RuntimeState.CREATED: {RuntimeState.INITIALIZING, RuntimeState.SHUTDOWN},
    RuntimeState.INITIALIZING: {RuntimeState.READY, RuntimeState.FAILED, RuntimeState.SHUTDOWN},
    RuntimeState.READY: {RuntimeState.RUNNING, RuntimeState.SHUTDOWN, RuntimeState.CANCELLED},
    RuntimeState.RUNNING: {
        RuntimeState.WAITING,
        RuntimeState.PAUSED,
        RuntimeState.COMPLETED,
        RuntimeState.FAILED,
        RuntimeState.CANCELLED,
        RuntimeState.SHUTDOWN,
    },
    RuntimeState.WAITING: {RuntimeState.RUNNING, RuntimeState.PAUSED, RuntimeState.FAILED, RuntimeState.SHUTDOWN},
    RuntimeState.PAUSED: {RuntimeState.RUNNING, RuntimeState.CANCELLED, RuntimeState.SHUTDOWN},
    RuntimeState.COMPLETED: {RuntimeState.SHUTDOWN},
    RuntimeState.FAILED: {RuntimeState.SHUTDOWN, RuntimeState.CANCELLED},
    RuntimeState.CANCELLED: {RuntimeState.SHUTDOWN},
    RuntimeState.SHUTDOWN: set(),
}


class InvalidStateTransitionError(RuntimeError):
    """Raised when an illegal state transition is requested."""

    def __init__(self, from_state: RuntimeState, to_state: RuntimeState):
        super().__init__(f"Invalid transition from {from_state} to {to_state}")
        self.from_state = from_state
        self.to_state = to_state


class RuntimeStateMachine:
    """Encapsulates the current state and provides a safe transition method.

    The engine or the :class:`StateManager` should use this class to move
    between states.
    """

    def __init__(self, initial_state: RuntimeState = RuntimeState.CREATED):
        self._state: RuntimeState = initial_state

    @property
    def state(self) -> RuntimeState:
        return self._state

    def can_transition(self, to_state: RuntimeState) -> bool:
        """Return ``True`` if a transition from the current state to ``to_state`` is allowed."""

        return to_state in _ALLOWED_TRANSITIONS.get(self._state, set())

    def transition(self, to_state: RuntimeState) -> None:
        """Perform a state transition after validating it.

        Raises
        ------
        InvalidStateTransitionError
            If the transition is not permitted.
        """

        if not self.can_transition(to_state):
            raise InvalidStateTransitionError(self._state, to_state)
        self._state = to_state

    def __repr__(self) -> str:
        return f"<RuntimeStateMachine state={self._state}>"

__all__ = ["RuntimeState", "RuntimeStateMachine", "InvalidStateTransitionError"]
