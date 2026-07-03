# framework/runtime/dummy_planner.py
"""A minimal Planner implementation for prototyping.

The planner conforms to :class:`PlannerInterface` and simply returns a callable
(plan) that echoes the workflow name and any supplied keyword arguments.  This
is sufficient for the initial demo of the RuntimeEngine.
"""

from __future__ import annotations

from typing import Any

from .interfaces import PlannerInterface


class DummyPlanner(PlannerInterface):
    """Very simple planner used for early integration tests.

    The ``plan`` method returns a callable that, when invoked, produces a
    dictionary containing the workflow name and the arguments it received.
    """

    def initialize(self) -> None:
        # No heavy initialization required for the dummy planner.
        pass

    def plan(self, workflow_name: str, context: Any) -> Any:
        """Return a callable representing the execution plan.

        Parameters
        ----------
        workflow_name: str
            Name of the workflow to be executed.
        context: Any
            The :class:`RuntimeContext` (unused in this dummy implementation).
        """

        def execution_plan(**kwargs: Any) -> dict:
            return {
                "workflow": workflow_name,
                "status": "planned",
                "kwargs": kwargs,
            }

        return execution_plan

__all__ = ["DummyPlanner"]
