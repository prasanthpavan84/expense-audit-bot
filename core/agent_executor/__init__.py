# core/agent_executor/__init__.py
"""Simple agent executor stub.

In the full system this would coordinate the execution of individual agents
based on a workflow graph. For the prototype we provide a no‑op implementation
that satisfies the expected interface.
"""

from __future__ import annotations

from typing import Any


class SimpleAgentExecutor:
    """Placeholder executor that pretends to run agents.

    The ``execute`` method accepts an ``agent`` (any callable) and forwards any
    kwargs. It returns the result of the callable. This mirrors the contract of
    a more sophisticated executor without adding complexity.
    """

    def __init__(self) -> None:
        pass

    def execute(self, agent: Any, **kwargs: Any) -> Any:
        if not callable(agent):
            raise TypeError("Agent must be callable")
        return agent(**kwargs)
