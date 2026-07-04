# core/agents/base_agent.py
"""Base agent infrastructure providing a full lifecycle for all agents.

The design mirrors a typical Clean Architecture service layer where each
agent receives its required dependencies via a `ServiceContainer`.  The
container is expected to expose attributes such as `event_bus`, `memory`,
`logger`, and `config`.  Individual agents subclass :class:`BaseAgent`
and implement the :meth:`execute` method.  Optional lifecycle hooks can be
overridden to customise behaviour.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WorkflowContext:
    """Mutable context passed through the agent pipeline.

    Agents may read from and write to ``data`` to share information.
    ``metadata`` can hold auxiliary information such as timestamps or
    request identifiers.
    """

    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def update(self, mapping: Dict[str, Any]) -> None:
        self.data.update(mapping)


@dataclass
class AgentResult:
    """Standard result returned by an agent after successful execution.

    ``success`` indicates whether the agent believes the operation
    succeeded. ``output`` holds the primary payload (e.g. a parsed receipt,
    a risk score, etc.). ``explanation`` can contain a human‑readable
    justification for the result – useful for the explainability layer.
    """

    success: bool
    output: Any = None
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(abc.ABC):
    """Abstract base class defining the full agent lifecycle.

    Sub‑classes should only implement :meth:`execute`.  All other hooks are
    optional and can be overridden to perform setup, validation,
    post‑processing, cleanup, or rollback logic.
    """

    def __init__(
        self,
        *,
        event_bus: Any = None,
        memory: Any = None,
        logger: Optional[logging.Logger] = None,
        config: Dict[str, Any] | None = None,
        **extra_services,
    ) -> None:
        # ``extra_services`` allows the container to pass any additional
        # components without breaking the signature.
        self.event_bus = event_bus
        self.memory = memory
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.config = config or {}
        self.name = extra_services.get("name") or self.__class__.__name__
        self.extra_services = extra_services
        for k, v in extra_services.items():
            setattr(self, k, v)
        self.initialize()



    # ---------------------------------------------------------------------
    # Lifecycle hooks – default implementations are no‑ops.  Sub‑classes can
    # override any of these as needed.
    # ---------------------------------------------------------------------
    def initialize(self) -> None:
        """Perform one‑time initialisation.

        Called from ``__init__`` after dependencies have been assigned.
        """

        self.logger.debug("%s.initialized", self.__class__.__name__)

    def pre_execute(self, ctx: WorkflowContext) -> None:
        """Hook executed **before** the main ``execute`` call.

        Agents can mutate ``ctx`` to add derived inputs.
        """

        self.logger.debug("%s.pre_execute", self.__class__.__name__)

    @abc.abstractmethod
    def execute(self, ctx: WorkflowContext) -> AgentResult:
        """Core business logic for the agent.

        Must return an :class:`AgentResult` instance.
        """

    def validate(self, result: AgentResult) -> None:
        """Validate the result after execution.

        The default implementation raises ``ValueError`` if ``result.success``
        is ``False``.  Sub‑classes may perform richer validation.
        """

        # No-op by default so that use cases can handle FAILED status gracefully.
        self.logger.debug("%s.validate passed", self.__class__.__name__)

    def post_execute(self, result: AgentResult) -> None:
        """Hook executed **after** successful validation.

        Useful for emitting events, persisting state, or augmenting the
        result with additional metadata.
        """

        self.logger.debug("%s.post_execute", self.__class__.__name__)

    def cleanup(self) -> None:
        """Release any resources held by the agent.

        Called in a ``finally`` block to guarantee execution even on error.
        """

        self.logger.debug("%s.cleanup", self.__class__.__name__)

    def rollback(self) -> None:
        """Undo any side‑effects if the agent fails later in the pipeline.

        The default implementation is a stub; concrete agents should
        implement domain‑specific rollback logic.
        """

        self.logger.warning("%s.rollback invoked – no default behaviour", self.__class__.__name__)

    def explain(self, result: AgentResult) -> str:
        """Provide a human-readable justification of the agent decision/output."""
        return result.explanation or f"Agent {self.name} completed successfully."

    # ---------------------------------------------------------------------
    # Public entry point used by orchestration code.
    # ---------------------------------------------------------------------
    def run(self, ctx: Optional[WorkflowContext] = None) -> AgentResult:
        """Execute the full lifecycle and return an :class:`AgentResult`.

        ``ctx`` is optional – a fresh :class:`WorkflowContext` will be
        created if omitted.
        """

        ctx = ctx or WorkflowContext()
        try:
            self.pre_execute(ctx)
            result = self.execute(ctx)
            self.validate(result)
            self.post_execute(result)
            return result
        except Exception as exc:  # pragma: no cover – error path exercised by tests
            self.logger.exception("%s failed: %s", self.__class__.__name__, exc)
            # Attempt a rollback before re‑raising so that upstream callers can
            # decide how to handle the exception.
            try:
                self.rollback()
            finally:
                raise
        finally:
            self.cleanup()

    async def process_state(self, state: Any) -> Any:
        """Standardized method for processing workflow state.

        Bridges the legacy orchestrator's state-based pipeline to the Clean Architecture agents.
        """
        from core.validation.schemas import WorkflowContext
        from domain.receipt import Receipt
        from domain.policy import PolicyResult
        from domain.fraud import FraudResult

        # Build context
        context = WorkflowContext(input=state.raw_input)

        # Pull receipt if already extracted
        receipt_data = state.metadata.get("receipt_data")
        if receipt_data:
            try:
                context.receipt = Receipt(**receipt_data)
            except Exception:
                pass
        elif state.expenses:
            exp = state.expenses[0]
            context.receipt = Receipt(
                raw_text=state.raw_input,
                merchant_name=exp.merchant,
                amount=exp.amount,
                currency=exp.currency or "USD",
                date=exp.date or "Unknown",
                ocr_confidence_score=exp.confidence_score
            )

        # Pull other intermediate results
        if "validation_errors" in state.metadata:
            context.metadata["validation_errors"] = state.metadata["validation_errors"]

        # Carry over all metadata
        context.metadata.update(state.metadata)

        # Run the agent
        res = self.run(context)

        # Propagate outputs back to state
        agent_name = (self.name or self.__class__.__name__).lower()

        if agent_name in ["receipt_extractor", "extractionagent"] and res.success and res.output:
            receipt = res.output
            state.metadata["receipt_data"] = receipt.model_dump()
            from app.models.state import ExpenseItem

            category = "Other"
            merchant_lower = receipt.merchant_name.lower()
            text_lower = receipt.raw_text.lower() if receipt.raw_text else ""
            if "meal" in text_lower or "food" in text_lower or "starbucks" in merchant_lower:
                category = "Meals"
            elif "hotel" in text_lower or "stay" in text_lower or "hilton" in merchant_lower:
                category = "Hotel"
            elif "uber" in merchant_lower or "taxi" in merchant_lower or "ride" in merchant_lower:
                category = "Taxi"
            elif "flight" in text_lower:
                category = "Flight"
            elif "software" in text_lower:
                category = "Software"

            try:
                exp_item = ExpenseItem(
                    category=category,
                    amount=receipt.amount,
                    currency=receipt.currency,
                    date=receipt.date if receipt.date != "Unknown" else "",
                    merchant=receipt.merchant_name,
                    description=receipt.raw_text,
                    confidence_score=receipt.ocr_confidence_score
                )
                state.expenses = [exp_item]
            except Exception as exc:
                # Capture the validation errors from Pydantic validator
                errors = []
                if hasattr(exc, "errors"):
                    for err in exc.errors():
                        errors.append(f"{err.get('loc')[0]}: {err.get('msg')}")
                else:
                    errors.append(str(exc))
                state.metadata["validation_errors"] = errors
                state.expenses = []

        elif agent_name in ["validation_agent", "validationagent"]:
            if not res.success:
                state.metadata["validation_errors"] = res.output
            else:
                state.metadata.pop("validation_errors", None)

        elif agent_name in ["policy_agent", "policyagent"] and res.output:
            policy_res = res.output
            from app.models.state import AuditResult
            audit_res = state.audit_results.get("expense_0") or AuditResult()
            audit_res.policy_violations = policy_res.violations
            audit_res.is_approved = (len(policy_res.violations) == 0 and audit_res.fraud_score <= 50)
            state.audit_results["expense_0"] = audit_res
            state.metadata["policy_checks"] = {v: True for v in policy_res.violations}

        elif agent_name in ["fraud_agent", "fraudagent"] and res.output:
            fraud_res = res.output
            from app.models.state import AuditResult
            audit_res = state.audit_results.get("expense_0") or AuditResult()
            audit_res.fraud_score = int(fraud_res.score * 100)
            audit_res.is_approved = (audit_res.fraud_score <= 50 and len(audit_res.policy_violations) == 0)
            state.audit_results["expense_0"] = audit_res
            state.metadata["fraud_indicators"] = fraud_res.indicators

        elif agent_name in ["report_agent", "reportagent"] and res.output:
            report = res.output
            state.metadata["report"] = report.model_dump()
            state.metadata["response"] = report.summary

        # Sync metadata back to state
        for k, v in context.metadata.items():
            if k not in ["receipt_data", "validation_errors", "policy_checks", "fraud_indicators"]:
                state.metadata[k] = v

        return state


__all__ = [
    "WorkflowContext",
    "AgentResult",
    "BaseAgent",
]
