# core/planner/__init__.py
"""Planner that orchestrates the business agents.

The planner builds an execution *plan* – a callable that runs the agents
sequentially using :class:`SimpleAgentExecutor`. Each agent stores its
output in a shared :class:`WorkflowContext` so downstream agents can access
previous results.
"""

from __future__ import annotations

from typing import Any, Callable

# Local imports – delayed to avoid circular dependencies when the module is
# imported during the runtime boot process.
from core.agent_executor import SimpleAgentExecutor
from core.agents.base_agent import WorkflowContext, AgentResult


class SimplePlanner:
    """Generate a plan that executes all business agents in order.

    The returned ``plan`` callable receives ``**kwargs`` (currently ignored) and
    runs the agents sequentially. The final ``AgentResult`` from the
    ``ReportAgent`` is returned to the caller.
    """

    def __init__(self) -> None:
        # Lazily import agents to avoid circular imports.
        from core.agents.ocr_agent import OCRAgent
        from core.agents.receipt_analysis_agent import ReceiptAnalysisAgent
        from core.agents.validation_agent import ValidationAgent
        from core.agents.fraud_detection_agent import FraudDetectionAgent
        from core.agents.policy_agent import PolicyAgent
        from core.agents.reflection_agent import ReflectionAgent
        from core.agents.report_agent import ReportAgent

        self._agents = [
            OCRAgent(),
            ReceiptAnalysisAgent(),
            ValidationAgent(),
            FraudDetectionAgent(),
            PolicyAgent(),
            ReflectionAgent(),
            ReportAgent(),
        ]
        self._executor = SimpleAgentExecutor()

    def initialize(self) -> None:
        """No special initialization required for this mock planner."""

    def plan(self, workflow_name: str, context: Any) -> Callable[..., Any]:
        """Return a callable that runs the agent chain.

        ``workflow_name`` and ``context`` are currently unused – the same static
        chain is executed for any request.
        """

        def _plan(**kwargs: Any) -> AgentResult:
            # Shared mutable context for agents.
            wf_ctx = WorkflowContext()
            result: AgentResult | None = None
            for agent in self._agents:
                result = self._executor.execute(agent, ctx=wf_ctx)
            assert result is not None
            return result

        return _plan
