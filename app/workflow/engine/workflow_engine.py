import time
import uuid

from app.core.config_manager import config
from app.core.event_bus import EventBus
from app.registry.agent_registry import agent_registry
from app.repositories.audit_repository import AuditRepository
from app.repositories.event_repository import EventRepository
from app.utils.logger import get_logger, log_pipeline_stage, trace_id_var
from app.workflow.executors.checkpoint_executor import CheckpointExecutor
from app.workflow.validators.workflow_validator import WorkflowValidator
from core.validation.schemas import WorkflowContext


class WorkflowEngine:
    """Core Workflow Engine that dynamically executes configured agent sequences and handles resilience."""

    def __init__(
        self,
        validator: WorkflowValidator | None = None,
        checkpointer: CheckpointExecutor | None = None,
        event_repository: EventRepository | None = None,
        audit_repository: AuditRepository | None = None,
        event_bus: EventBus | None = None,
    ):
        self.validator = validator or WorkflowValidator()
        self.checkpointer = checkpointer or CheckpointExecutor()
        self.event_repository = event_repository or EventRepository()
        self.audit_repository = audit_repository or AuditRepository()
        self.event_bus = event_bus or EventBus()
        self.logger = get_logger("WorkflowEngine")

    async def execute_workflow(
        self,
        workflow_name: str,
        raw_input: str,
        audit_id: str | None = None,
        correlation_id: str | None = None,
        user_role: str = "Associate",
        justification: str | None = None,
    ) -> WorkflowContext:
        """Run the specified workflow sequence from definitions, supporting recovery from checkpoints."""

        # 1. Initialize identifiers
        audit_id = audit_id or f"audit-{str(uuid.uuid4())[:8]}"
        correlation_id = correlation_id or f"corr-{str(uuid.uuid4())[:8]}"

        # Set trace ID ContextVar
        trace_id_var.set(correlation_id)

        # Check for existing checkpoint
        checkpoint = self.checkpointer.restore_checkpoint(audit_id)
        if checkpoint:
            last_step, state_data = checkpoint
            self.logger.info(f"Checkpoint found! Resuming audit '{audit_id}' from step '{last_step}'.")
            context = WorkflowContext(**state_data)
            # Restore inputs
            context.input = raw_input
        else:
            last_step = None
            context = WorkflowContext(input=raw_input)
            context.metadata.update(
                {
                    "audit_id": audit_id,
                    "correlation_id": correlation_id,
                    "user_role": user_role,
                    "justification": justification,
                    "report_format": "markdown",
                    "start_time": time.time(),
                }
            )

        # 3. Load agent sequence
        steps = self.validator.workflows.get(workflow_name)
        if not steps:
            raise ValueError(f"Workflow '{workflow_name}' not defined in config.")

        # If we have a checkpoint, slice steps to resume from next step
        if last_step and last_step in steps:
            resume_idx = steps.index(last_step) + 1
            steps_to_run = steps[resume_idx:]
        else:
            steps_to_run = steps

        # Publish WorkflowStarted event
        start_payload = {"workflow": workflow_name, "steps": steps, "correlation_id": correlation_id}
        self.event_bus.publish("WorkflowStarted", start_payload)
        self.event_repository.save_event(audit_id, correlation_id, "WorkflowEngine", "WorkflowStarted", start_payload)

        # 4. Sequential execution loop
        for step in steps_to_run:
            agent_instance = agent_registry.get_agent(step)
            if not agent_instance:
                # Fallback mapping for standard names
                agent_name_map = {
                    "receipt_extractor": "receipt_extractor",
                    "policy_agent": "policy_agent",
                    "fraud_agent": "fraud_agent",
                    "reasoning_agent": "reasoning_agent",
                    "reflection_agent": "reflection_agent",
                    "report_agent": "report_agent",
                    "query_agent": "query_agent",
                }
                mapped_name = agent_name_map.get(step, step)
                agent_instance = agent_registry.get_agent(mapped_name)

            if not agent_instance:
                raise ValueError(f"Agent '{step}' not found in registry.")

            # Set agent metadata on registry config if needed
            agent_instance.name = step

            # Publish AgentStarted event
            self.event_bus.publish("AgentStarted", {"agent": step, "audit_id": audit_id})
            self.event_repository.save_event(
                audit_id, correlation_id, step, "AgentStarted", {"correlation_id": correlation_id}
            )

            # Run agent with retry and fallback policy
            retry_count = config.max_iterations
            agent_success = False
            result = None

            for attempt in range(retry_count):
                try:
                    start_time = time.time()
                    # Execute agent
                    result = agent_instance.run(context)
                    latency = (time.time() - start_time) * 1000.0
                    duration = latency / 1000.0

                    if result.success:
                        agent_success = True
                        # Record event success
                        completed_payload = {
                            "status": "COMPLETED",
                            "latency_ms": latency,
                            "explanation": result.explanation,
                        }
                        self.event_bus.publish("AgentCompleted", {"agent": step, **completed_payload})
                        self.event_repository.save_event(
                            audit_id, correlation_id, step, "AgentCompleted", completed_payload
                        )

                        # Call stage logger
                        warnings_count = len(context.metadata.get("policy_violations", [])) + len(
                            context.metadata.get("fraud_indicators", [])
                        )
                        log_pipeline_stage(
                            session_id=context.metadata.get("session_id") or correlation_id or "unknown",
                            audit_id=audit_id,
                            stage=step,
                            duration=duration,
                            decision="COMPLETED",
                            confidence=getattr(result, "confidence", 1.0),
                            errors=[],
                            warning_count=warnings_count,
                        )
                        break
                    else:
                        self.logger.warning(
                            f"Agent '{step}' returned unsuccessful result (Attempt {attempt+1}/{retry_count}): {result.explanation}"
                        )
                        log_pipeline_stage(
                            session_id=context.metadata.get("session_id") or correlation_id or "unknown",
                            audit_id=audit_id,
                            stage=step,
                            duration=duration,
                            decision="FAILED",
                            confidence=0.0,
                            errors=[result.explanation],
                            warning_count=0,
                        )
                except Exception as e:
                    self.logger.error(f"Error executing agent '{step}' (Attempt {attempt+1}/{retry_count}): {e!s}")
                    log_pipeline_stage(
                        session_id=context.metadata.get("session_id") or correlation_id or "unknown",
                        audit_id=audit_id,
                        stage=step,
                        duration=0.0,
                        decision="EXCEPTION",
                        confidence=0.0,
                        errors=[str(e)],
                        warning_count=0,
                    )

            if not agent_success:
                # Fallback mode: use cached mock results or raise error
                self.logger.error(f"Agent '{step}' failed all retry attempts. Executing fallback.")
                # We can generate a generic fallback result to continue
                fallback_explanation = f"Agent '{step}' failed. Executed fallback configuration."
                # Publish event
                self.event_repository.save_event(
                    audit_id, correlation_id, step, "AgentFailed", {"explanation": fallback_explanation}
                )

                # Resilient recovery: save checkpoint and return context with failure status
                if hasattr(context, "model_dump"):
                    state_snapshot = context.model_dump()
                else:
                    state_snapshot = context.dict()
                self.checkpointer.save_checkpoint(audit_id, correlation_id, step, state_snapshot)
                context.metadata["workflow_status"] = "FAILED"
                context.metadata["failure_step"] = step
                return context

            # Save checkpoint after each successful step
            if hasattr(context, "model_dump"):
                state_snapshot = context.model_dump()
            else:
                state_snapshot = context.dict()
            self.checkpointer.save_checkpoint(audit_id, correlation_id, step, state_snapshot)

        # 5. Finalize execution
        self.checkpointer.clear_checkpoint(audit_id)
        context.metadata["workflow_status"] = "COMPLETED"

        # Save finalized audit to AuditRepository if it is an AUDIT workflow
        if workflow_name == "AUDIT":
            from app.models.domain import Expense

            receipt = context.get("receipt")
            needs_review = context.metadata.get("needs_human_review", False)
            violations = context.metadata.get("policy_violations", [])

            final_status = "Approved"
            if violations:
                final_status = "Rejected"
            if needs_review:
                final_status = "Needs Human Review"

            expense = Expense(
                id=audit_id,
                employee_id=user_role,
                merchant=receipt.merchant_name if receipt else "Unknown",
                date=receipt.date if receipt else "Unknown",
                amount=receipt.amount if receipt else 0.0,
                currency=receipt.currency if receipt else "USD",
                category=receipt.category if (receipt and hasattr(receipt, "category")) else "Other",
                status=final_status,
                reimbursable=context.metadata.get("reimbursable_amount", 0.0),
                rejected=context.metadata.get("rejected_amount", 0.0),
            )
            self.audit_repository.save(expense)

        # Publish WorkflowCompleted event
        end_payload = {"status": "COMPLETED", "duration_sec": time.time() - context.metadata["start_time"]}
        self.event_bus.publish("WorkflowCompleted", end_payload)
        self.event_repository.save_event(audit_id, correlation_id, "WorkflowEngine", "WorkflowCompleted", end_payload)

        return context
