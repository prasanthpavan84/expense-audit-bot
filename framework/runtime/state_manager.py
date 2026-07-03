# framework/runtime/state_manager.py
"""StateManager coordinates runtime state transitions.

It holds a :class:`RuntimeStateMachine` instance and provides a thin API
for the :class:`RuntimeEngine` and other components to query or change the
current lifecycle state.  The manager does **not** act as a service locator –
it operates solely on the injected ``RuntimeContext`` and the FSM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .runtime_state import RuntimeState, RuntimeStateMachine, InvalidStateTransitionError
from .runtime_context import RuntimeContext


@dataclass
class StateManager:
    """Manage the lifecycle state of the runtime.

    Parameters
    ----------
    context: RuntimeContext
        The execution context injected by :class:`RuntimeEngine`.
    state_machine: Optional[RuntimeStateMachine]
        Allows injection of a custom FSM (e.g., for testing).  If omitted a
        fresh ``RuntimeStateMachine`` starting at ``RuntimeState.CREATED`` is
        created.
    """

    context: RuntimeContext
    state_machine: RuntimeStateMachine = None

    def __post_init__(self) -> None:
        if self.state_machine is None:
            self.state_machine = RuntimeStateMachine()
        # Expose the initial state in the context for visibility.
        self.context.set_state("runtime_state", str(self.state_machine.state))

    @property
    def state(self) -> RuntimeState:
        """Current lifecycle state."""
        return self.state_machine.state

    def transition(self, to_state: RuntimeState) -> None:
        """Transition to ``to_state`` if permitted.

        Raises
        ------
        InvalidStateTransitionError
            If the transition is not allowed by the FSM.
        """
        try:
            self.state_machine.transition(to_state)
        except InvalidStateTransitionError as exc:
            # Propagate with a richer message.
            raise InvalidStateTransitionError(exc.from_state, exc.to_state) from exc
        # Keep the context in sync for any observers.
        self.context.set_state("runtime_state", str(self.state_machine.state))

    def can_transition(self, to_state: RuntimeState) -> bool:
        """Return ``True`` if a transition to ``to_state`` is allowed."""
        return self.state_machine.can_transition(to_state)

__all__ = ["StateManager"]
