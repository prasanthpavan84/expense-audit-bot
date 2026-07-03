# core/workflow_executor/__init__.py
"""Simple workflow executor for the expense audit bot.

It receives a callable *plan* (produced by the planner) and executes it with any
provided keyword arguments. In a full implementation this would orchestrate a
graph of agents, handle retries, and manage state; for the prototype we keep it
trivial.
"""

from __future__ import annotations

from typing import Any, Callable


class SimpleWorkflowExecutor:
    """Execute a plan callable and return its result.

    The ``execute`` method mirrors the expected interface of a more complex
    executor: it accepts a ``plan`` (any callable) and forwards ``kwargs``.
    """

    def __init__(self) -> None:
        pass

    def execute(self, plan: Callable[..., Any], **kwargs: Any) -> Any:
        """Run the provided ``plan`` callable.

        Parameters
        ----------
        plan: Callable
            The execution plan returned by ``PlannerInterface.plan``.
        **kwargs: Any
            Arguments to forward to the plan.
        """
        if not callable(plan):
            raise TypeError("Plan must be callable")
        return plan(**kwargs)
