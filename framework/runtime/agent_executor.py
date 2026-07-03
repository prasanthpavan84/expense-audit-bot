# framework/runtime/agent_executor.py
"""AgentExecutor runs a registered agent with the provided RuntimeContext.

The executor abstracts the instantiation and execution of agents.  An agent
class is expected to accept a ``RuntimeContext`` in its constructor and expose
a ``run`` method that returns a result (any serialisable object).
"""

from __future__ import annotations

from typing import Any

from .registry import Registry
from .runtime_context import RuntimeContext


class AgentExecutor:
    """Execute agents fetched from the :class:`Registry`.

    Parameters
    ----------
    registry: Registry
        The central registry containing agent class mappings.
    """

    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def run_agent(self, name: str, context: RuntimeContext) -> Any:
        """Instantiate and run the agent identified by ``name``.

        Returns the value produced by the agent's ``run`` method.
        """
        agent_cls = self.registry.get_agent(name)
        agent = agent_cls(context)
        # Agents are expected to implement ``run``.
        return agent.run()

__all__ = ["AgentExecutor"]
