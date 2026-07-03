# framework/runtime/workflow_executor.py
"""WorkflowExecutor coordinates the execution of an execution plan.

The executor receives a *plan* (produced by the Planner) and an
``AgentExecutor``.  The plan is expected to be a callable that, when invoked,
returns an ordered list of agent names that should be run for the workflow.

For the foundation phase the executor is deliberately simple:
* Call the plan to obtain the list of agent identifiers.
* Iterate over the identifiers and ask ``AgentExecutor`` to run each
  agent with the shared ``RuntimeContext``.
* Collect each agent's result into a dictionary keyed by the agent name and
  return that dictionary.

This design keeps the RuntimeEngine lightweight – it only needs to hand the
plan to the executor.  More sophisticated behaviours (parallelism, retries,
error handling) can be added later without touching the engine.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from .agent_executor import AgentExecutor
from .runtime_context import RuntimeContext


class WorkflowExecutor:
    """Execute a workflow plan using an ``AgentExecutor``.

    Parameters
    ----------
    agent_executor: AgentExecutor
        Executes individual agents by name.
    """

    def __init__(self, agent_executor: AgentExecutor) -> None:
        self.agent_executor = agent_executor

    def run(self, plan: Callable[[RuntimeContext], List[str]], context: RuntimeContext) -> Dict[str, Any]:
        """Run the provided ``plan`` and collect agent results.

        The ``plan`` callable receives the ``RuntimeContext`` and must return a
        list of agent names (strings) in the order they should be executed.
        """
        # Obtain the ordered list of agent identifiers.
        agent_names: List[str] = plan(context)
        results: Dict[str, Any] = {}
        for name in agent_names:
            results[name] = self.agent_executor.run_agent(name, context)
        return results

__all__ = ["WorkflowExecutor"]
