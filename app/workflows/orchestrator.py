"""Workflow Orchestrator — v2 (Hardened).

Implements the full 22-stage cognitive pipeline:
  1. Input Validation → 2. Normalization → 3. Input Quality → 4. Noise Detection
  → 5. Receipt Detection → 6. Entity Extraction → 7. Intent Classification
  → 8. Intent Verification → 9. Context Merge → 10. Multi-Intent Resolution
  → 11. Conversation Firewall → 12. Safety Rules → 13. Cognitive Decision
  → 14. Planner → 15. Authorization → 16. Execution → 17. Reflection
  → 18. Response Validation → 19. Final Response

No stage may be skipped. Every stage returns structured metadata.
"""

import asyncio
import time
import uuid
import traceback
from typing import Optional

from app.models.state import WorkflowState
from app.core.agent_registry import registry
from app.utils.logger import get_logger, TraceLogger
from app.workflows.router import IntentRouterAgent
from app.agents.extraction_agent import ExtractionAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.fraud_agent import FraudAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.report_agent import ReportAgent
from app.agents.query_agent import QueryAgent
from app.agents.hallucination_agent import HallucinationAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.security_agent import SecurityAgent
from app.validation.response_validator import validate_response
from app.engine.cognitive_engine import CognitiveEngine, CognitiveDecision
from app.engine.exceptions import (
    ConversationFirewallViolation,
    WorkflowAuthorizationError,
)
from app.intents.intent_engine import IntentEngine, CONVERSATION_INTENTS


# Register all agents
registry.register("intent_router", IntentRouterAgent())
registry.register("receipt_extractor", ExtractionAgent())
registry.register("policy_agent", PolicyAgent())
registry.register("fraud_agent", FraudAgent())
registry.register("validation_agent", ValidationAgent())
registry.register("report_agent", ReportAgent())
registry.register("query_agent", QueryAgent())
registry.register("hallucination_agent", HallucinationAgent())
registry.register("reflection_agent", ReflectionAgent())
registry.register("security_agent", SecurityAgent())

# Expense agents that are guarded by the conversation firewall
_EXPENSE_AGENTS = frozenset({
    "receipt_extractor", "validation_agent", "policy_agent",
    "fraud_agent", "reflection_agent", "report_agent",
    "hallucination_agent", "query_agent",
})


class WorkflowOrchestrator:
    """Coordinates the execution of agents through the hardened cognitive pipeline."""

    def __init__(self):
        pass

    async def run(self, raw_input: str, state: WorkflowState = None) -> WorkflowState:
        """Main entry point for executing the bot workflow."""
        if state is None:
            state = WorkflowState(raw_input=raw_input)
        else:
            state.raw_input = raw_input

        # Generate trace_id for telemetry
        trace_id = str(uuid.uuid4())
        state.metadata["trace_id"] = trace_id
        logger = TraceLogger(get_logger(), trace_id)
        logger.info(f"Starting workflow execution for input: {raw_input[:50]}...")

        state.create_snapshot()

        # ===== GATE 1: Security Guard =====
        state = await self._execute_agent("security_agent", state)
        if state.metadata.get("security_error"):
            state = await self._execute_agent("report_agent", state)
            return state

        # ===== GATE 2-7: Intent Classification Pipeline =====
        # The router internally runs: normalization → input type → noise →
        # receipt detection → entity extraction → intent classification
        state = await self._execute_agent("intent_router", state)
        state.create_snapshot()

        # ===== GATE 8-9: Context Manager =====
        from app.intents.context_manager import ContextManager
        from app.workflows.planner import select_workflow

        # Clear stale state if this is a new, unrelated conversation
        self._clear_stale_state_if_needed(state)

        state = ContextManager.resolve_follow_up(state)
        state = ContextManager.update(state)

        # ===== GATE 10-13: Cognitive Decision Engine =====
        # select_workflow() internally calls CognitiveEngine.decide() and
        # then WorkflowPlanner.plan_from_decision()
        plan = select_workflow(state)
        state.metadata["workflow_plan"] = {
            "steps": plan.steps,
            "intent": plan.intent,
            "reason": plan.reason,
            "suitability_score": plan.suitability_score,
            "preconditions_met": plan.preconditions_met,
            "decision_explanation": plan.decision_explanation,
        }
        state.metadata["ai_readiness"] = plan.readiness
        state.metadata["planner_decision"] = plan.decision_explanation

        # Log cognitive decision
        cognitive = state.metadata.get("cognitive_decision")
        if cognitive:
            logger.info(
                f"Cognitive Decision: next_action={cognitive.next_action}, "
                f"firewall={'PASS' if cognitive.firewall_passed else 'BLOCK'}, "
                f"intent={cognitive.intent.stage2_intent}, "
                f"confidence={cognitive.intent.confidence:.3f}"
            )

        # ===== GATE 14: Conversation Firewall Enforcement =====
        if not plan.preconditions_met and not plan.steps:
            if plan.intent == "CONVERSATION":
                # Direct conversational response
                stage2 = ""
                if cognitive:
                    stage2 = cognitive.intent.stage2_intent

                state.metadata["response"] = self._get_conversation_response(stage2)
                state.status = "COMPLETED"
                ContextManager.transition_to(state, "COMPLETING")
                ContextManager.transition_to(state, "ENDED")
                return state
            else:
                # Clarification needed
                state.metadata["needs_clarification"] = True
                state.metadata["clarification_question"] = plan.reason
                state.status = "CLARIFY"
                ContextManager.transition_to(state, "CLARIFYING")
                ContextManager.set_pending_intent(state, plan.intent)
                return state

        if not plan.steps and plan.intent == "CONVERSATION":
            stage2 = ""
            if cognitive:
                stage2 = cognitive.intent.stage2_intent
            state.metadata["response"] = self._get_conversation_response(stage2)
            state.status = "COMPLETED"
            ContextManager.transition_to(state, "COMPLETING")
            ContextManager.transition_to(state, "ENDED")
            return state

        # ===== GATE 15: Authorization Enforcement =====
        if plan.authorization is None and plan.steps:
            raise WorkflowAuthorizationError(
                "Workflow has steps but no ExecutionAuthorization token.",
                context={"intent": plan.intent, "steps": plan.steps},
            )

        # ===== GATE 16: Execution =====
        for step in plan.steps:
            # Firewall check before each agent
            CognitiveEngine.validate_firewall(
                plan.intent, step
            )
            state = await self._execute_agent(step, state)

        # Clear pending intent upon successful execution
        ContextManager.clear_pending_intent(state)

        # ===== GATE 17-18: Reflection & Response Validation =====
        if not validate_response(state):
            ContextManager.transition_to(state, "CLARIFYING")
            return state

        ContextManager.transition_to(state, "COMPLETING")
        ContextManager.transition_to(state, "ENDED")
        return state

    async def _execute_agent(
        self, agent_name: str, state: WorkflowState,
        timeout: float = 10.0, retries: int = 1,
    ) -> WorkflowState:
        agent = registry.get_agent(agent_name)
        trace_id = state.metadata.get("trace_id", "unknown")
        logger = TraceLogger(get_logger(), trace_id)

        for attempt in range(retries + 1):
            try:
                logger.info(f"Starting agent: {agent_name} (Attempt {attempt + 1})")
                start_time = time.time()
                state = await asyncio.wait_for(agent.process_state(state), timeout=timeout)
                duration = time.time() - start_time

                if "performance" not in state.metadata:
                    state.metadata["performance"] = {}
                state.metadata["performance"][agent_name] = duration
                logger.info(f"Completed agent: {agent_name} in {duration:.3f}s")
                return state

            except TimeoutError:
                logger.error(f"Agent {agent_name} timed out after {timeout}s")
                if attempt == retries:
                    raise
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {str(e)}\n{traceback.format_exc()}")
                if attempt == retries:
                    raise
        return state

    @staticmethod
    def _get_conversation_response(stage2_intent: str) -> str:
        """Return an appropriate conversational response."""
        responses = {
            "GREETING": "Hello! I am your Expense Audit assistant. How can I help you today?",
            "FAREWELL": "Goodbye! Feel free to come back whenever you need help with expenses.",
            "THANKS": "You're welcome! Is there anything else I can help you with?",
            "HELP": (
                "I can help you with:\n"
                "• Auditing expense receipts\n"
                "• Checking company policies\n"
                "• Querying expense data\n"
                "• Detecting fraud in receipts\n"
                "Just describe your expense or ask a question!"
            ),
            "SMALL_TALK": "I appreciate the chat! I'm best at helping with expense audits. How can I assist you?",
            "GENERAL_KNOWLEDGE": "I'm specialized in expense auditing. I can help with receipts, policies, and expense queries.",
            "UNKNOWN": "I'm not sure what you're asking. Could you please describe an expense to audit, or ask about a policy?",
            "RESTART": "Sure, let's start fresh! What would you like me to help with?",
            "CANCEL": "Okay, I've cancelled the current operation. What would you like to do next?",
        }
        return responses.get(stage2_intent, responses["UNKNOWN"])

    @staticmethod
    def _clear_stale_state_if_needed(state: WorkflowState) -> None:
        """Clear stale workflow state when a new unrelated conversation starts.

        If the current intent is conversational and there's no pending
        clarification, we clear previous workflow artifacts.
        """
        intent_decision = state.metadata.get("intent_decision")
        if not intent_decision:
            return

        stage2 = intent_decision.stage2_intent
        if stage2 not in CONVERSATION_INTENTS:
            return

        # Check for pending clarification — don't clear if user is responding
        context = state.metadata.get("context", {})
        if isinstance(context, dict) and context.get("pending_clarification_intent"):
            return

        # Clear stale workflow state
        stale_keys = [
            "extraction_results", "validation_errors", "policy_results",
            "fraud_results", "reflection_results", "report",
            "hallucination_errors", "hallucinations_detected",
        ]
        for key in stale_keys:
            state.metadata.pop(key, None)

        # Clear expenses
        state.expenses = []
        state.audit_results = {}
