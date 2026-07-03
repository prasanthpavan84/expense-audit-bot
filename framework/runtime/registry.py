# framework/runtime/registry.py
"""Simple in‑memory registry for agents and workflows.

The runtime needs a way to discover concrete agent classes and workflow
definitions without hard‑coding them.  This registry provides a minimal
lookup table that can be populated at start‑up (e.g., from a configuration
file) and queried by the :class:`AgentExecutor` and :class:`WorkflowExecutor`.

Only the features required for the foundation phase are implemented:

* Register an agent class under a string name.
* Retrieve a previously registered agent class.
* Register a workflow callable (or data structure) under a name.
* Retrieve a registered workflow.

The registry is deliberately lightweight – it stores raw callables / classes
and does **not** perform validation.  Validation will be added in later phases.
"""

from __future__ import annotations

from typing import Any, Callable, Dict


class Registry:
    """Container for agent and workflow registrations.

    Example usage:

    ```python
    from framework.runtime.registry import Registry
    registry = Registry()
    registry.register_agent("ocr", OCRAgent)
    agent_cls = registry.get_agent("ocr")
    ```
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._workflows: Dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Agent registration
    # ---------------------------------------------------------------------
    def register_agent(self, name: str, agent_cls: Any) -> None:
        """Register an agent class under ``name``.
        Overwrites any existing entry with the same name.
        """
        self._agents[name] = agent_cls

    def get_agent(self, name: str) -> Any:
        """Retrieve the agent class for ``name``.
        Raises ``KeyError`` if the name is unknown.
        """
        return self._agents[name]

    # ---------------------------------------------------------------------
    # Workflow registration
    # ---------------------------------------------------------------------
    def register_workflow(self, name: str, workflow_callable: Callable) -> None:
        """Register a workflow callable (or data structure) under ``name``.
        The callable should accept a ``RuntimeContext`` and return an execution
        plan that the ``WorkflowExecutor`` can consume.
        """
        self._workflows[name] = workflow_callable

    def get_workflow(self, name: str) -> Callable:
        """Retrieve the workflow callable for ``name``.
        Raises ``KeyError`` if the name is unknown.
        """
        return self._workflows[name]

    # ---------------------------------------------------------------------
    # Introspection helpers (useful for debugging and later UI)
    # ---------------------------------------------------------------------
    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def list_workflows(self) -> list[str]:
        return list(self._workflows.keys())

    def __repr__(self) -> str:
        return (
            f"<Registry agents={len(self._agents)} "
            f"workflows={len(self._workflows)}>")

__all__ = ["Registry"]
