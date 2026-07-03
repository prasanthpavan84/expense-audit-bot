# framework/runtime/runtime_engine.py
"""RuntimeEngine coordinates the execution of a workflow.

It glues together the ServiceContainer, StateManager, Scheduler, Planner,
and ArtifactManager.  The engine is deliberately lightweight – it provides
the plumbing for starting, running a named workflow, and shutting down.

The concrete implementations of SchedulerInterface, PlannerInterface and
ArtifactManagerInterface can be swapped out (e.g. for testing) because they
are injected via the ServiceContainer.
"""

from __future__ import annotations

from typing import Any

from ..container.service_container import ServiceContainer
from .runtime_context import RuntimeContext
from .runtime_state import RuntimeState, RuntimeStateMachine
from ..agents.base_agent import BaseAgent
from .interfaces import SchedulerInterface, PlannerInterface, ArtifactManagerInterface


class RuntimeEngine:
    """Core engine that drives the bot runtime.

    The engine maintains its own ``RuntimeStateMachine`` and works with a
    ``StateManager`` (which holds higher‑level run metadata).  All heavy
    lifting – scheduling, planning and artifact persistence – is delegated
    to the injected services.
    """

    def __init__(
        self,
        container: ServiceContainer,
        context: RuntimeContext,
        state_manager: Any,  # Expected to have ``transition`` method similar to StateManager
        scheduler: SchedulerInterface,
        planner: PlannerInterface,
        artifact_manager: ArtifactManagerInterface,
        workflow_executor: Any,  # Expected to follow WorkflowExecutor interface
        agent_executor: Any,  # Expected to follow AgentExecutor interface
    ) -> None:
        self.container = container
        self.context = context
        self.state_manager = state_manager
        self.scheduler = scheduler
        self.planner = planner
        self.artifact_manager = artifact_manager
        self.workflow_executor = workflow_executor
        self.agent_executor = agent_executor

        # Internal FSM for the engine lifecycle
        self._fsm = RuntimeStateMachine(RuntimeState.CREATED)

    # ---------------------------------------------------------------------
    # Lifecycle helpers
    # ---------------------------------------------------------------------
    def _transition(self, target: RuntimeState) -> None:
        """Perform a safe state transition and inform the StateManager.

        Parameters
        ----------
        target: RuntimeState
            Desired next state.
        """
        self._fsm.transition(target)
        # The injected ``state_manager`` follows the same API as the
        # ``StateManager`` defined in the framework package.
        if hasattr(self.state_manager, "transition"):
            self.state_manager.transition(target)

    def start(self) -> None:
        """Boot the runtime.

        The sequence mirrors the design from the implementation plan:

        1. ``CREATED`` → ``INITIALIZING``
        2. Initialise scheduler and any other services.
        3. ``INITIALIZING`` → ``READY``
        """
        self._transition(RuntimeState.INITIALIZING)
        # Initialise scheduler – concrete implementation decides what this means.
        if hasattr(self.scheduler, "start"):
            self.scheduler.start()
        self._transition(RuntimeState.READY)

    # ---------------------------------------------------------------------
    # Workflow execution
    # ---------------------------------------------------------------------
    def run_workflow(self, name: str, **kwargs: Any) -> Any:
        """Execute a workflow.

        The planner creates a plan object (opaque to the engine).  The engine
        then simply returns whatever the plan yields – in a real system this
        would involve walking through a graph of agents.
        """
        if self._fsm.state != RuntimeState.READY:
            raise RuntimeError("RuntimeEngine must be in READY state to run a workflow")

        self._transition(RuntimeState.RUNNING)

        # Ask the planner for a plan – the concrete type is implementation‑
        # defined, so we treat it as an opaque object.
        plan = self.planner.plan(name, self.context)

        # Delegate execution to the workflow executor.
        result = self.workflow_executor.execute(plan, **kwargs)


        self._transition(RuntimeState.COMPLETED)
        return result

    # ---------------------------------------------------------------------
    # Shutdown
    # ---------------------------------------------------------------------
    def shutdown(self) -> None:
        """Gracefully shutdown the runtime and all managed services."""
        # Allow services to clean up before the state machine reaches SHUTDOWN.
        if hasattr(self.scheduler, "stop"):
            self.scheduler.stop()
        self._transition(RuntimeState.SHUTDOWN)

    # ---------------------------------------------------------------------
    # Introspection helpers
    # ---------------------------------------------------------------------
    @property
    def state(self) -> RuntimeState:
        """Current engine state (read‑only)."""
        return self._fsm.state

    def __repr__(self) -> str:
        return f"<RuntimeEngine state={self.state}>"
