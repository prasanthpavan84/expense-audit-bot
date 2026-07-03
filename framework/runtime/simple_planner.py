# framework/runtime/simple_planner.py
"""A minimal Planner implementation that maps a workflow name to a list of agent names.

The planner conforms to :class:`PlannerInterface`.  The ``plan`` method returns
a *plan callable* that receives a ``RuntimeContext`` and returns the ordered
list of agent identifiers that should be executed for the requested workflow.

For the foundation phase the mapping is hard‑coded in ``WORKFLOWS``.  In later
phases the mapping can be loaded from configuration files or a database.
"""

from __future__ import annotations

from typing import Any, Callable, List

from .interfaces import PlannerInterface


# Hard‑coded workflow → agent list mapping
WORKFLOWS = {
    "demo_workflow": ["ocr", "receipt_analysis", "validation"],
}


class SimplePlanner(PlannerInterface):
    """Return a callable execution plan based on ``WORKFLOWS``.

    The returned callable receives the ``RuntimeContext`` (currently unused) and
    returns the list of agent names for the workflow.
    """

    def initialize(self) -> None:
        # No heavy initialization required for the simple planner.
        pass

    def plan(self, workflow_name: str, context: Any) -> Callable[[Any], List[str]]:
        """Create a plan callable for ``workflow_name``.

        Raises ``KeyError`` if the workflow is unknown.
        """

        agent_list = WORKFLOWS[workflow_name]

        def execution_plan(_: Any) -> List[str]:
            # The context could be used for dynamic plan generation later.
            return agent_list

        return execution_plan

__all__ = ["SimplePlanner"]
