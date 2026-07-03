"""Dynamic Workflow Planner — v2 (Hardened).

PLANNER CONTRACT:
  The Planner SHALL NOT: classify intent, override intent, infer user goals,
  request clarification, or perform safety decisions.

  The Planner SHALL ONLY: translate an approved CognitiveDecision into a
  workflow plan, validate workflow preconditions, and return ordered steps.

Core principle: THE AI MUST NEVER GUESS.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.state import WorkflowState
from app.engine.cognitive_engine import CognitiveDecision, ExecutionAuthorization
from app.engine.exceptions import PlannerValidationError
from app.intents.intent_engine import IntentEngine


@dataclass
class WorkflowPlan:
    """Dataclass holding the workflow execution plan."""
    steps: List[str]
    intent: str
    reason: str
    suitability_score: float
    preconditions_met: bool
    readiness: Dict[str, Any]
    decision_explanation: str
    authorization: Optional[ExecutionAuthorization] = None


# Valid agent sequences per workflow
_WORKFLOW_SEQUENCES: Dict[str, List[str]] = {
    "AUDIT": [
        "receipt_extractor", "hallucination_agent", "validation_agent",
        "policy_agent", "fraud_agent", "reflection_agent", "report_agent",
    ],
    "POLICY": ["policy_agent"],
    "QUERY": ["query_agent"],
    "CALCULATE": ["receipt_extractor", "report_agent"],
    "EXTRACT": ["receipt_extractor"],
}


class WorkflowPlanner:
    """Translates an approved CognitiveDecision into workflow steps.

    The planner contains ZERO cognitive logic — it is a pure translator.
    """

    @staticmethod
    def plan_from_decision(
        cognitive_decision: CognitiveDecision,
        state: WorkflowState,
    ) -> WorkflowPlan:
        """Generate a workflow plan from an approved CognitiveDecision.

        Raises ``PlannerValidationError`` if the decision is not approved.
        """
        intent_decision = cognitive_decision.intent
        auth = cognitive_decision.authorization

        readiness = {
            "intent_ready": True,
            "entities_ready": True,
            "context_ready": cognitive_decision.context_ready,
            "safety_passed": cognitive_decision.safety_checks_passed,
            "firewall_passed": cognitive_decision.firewall_passed,
            "suitability": 0.0,
            "user_role": state.metadata.get("user_role"),
        }

        # --- Conversation / non-executable intents ---
        if cognitive_decision.next_action == "RESPOND":
            return WorkflowPlan(
                steps=[],
                intent="CONVERSATION",
                reason="Conversational intent — no expense workflow.",
                suitability_score=1.0,
                preconditions_met=True,
                readiness=readiness,
                decision_explanation="Conversation firewall: direct response, no expense agents.",
                authorization=None,
            )

        # --- Clarification required ---
        if cognitive_decision.next_action == "CLARIFY":
            return WorkflowPlan(
                steps=[],
                intent=IntentEngine.map_to_workflow_intent(intent_decision.stage2_intent),
                reason=cognitive_decision.clarification_reason,
                suitability_score=intent_decision.confidence,
                preconditions_met=False,
                readiness=readiness,
                decision_explanation=f"Clarification required: {cognitive_decision.clarification_reason}",
                authorization=None,
            )

        # --- Blocked ---
        if cognitive_decision.next_action == "BLOCK":
            return WorkflowPlan(
                steps=[],
                intent="BLOCKED",
                reason="Execution blocked by safety checks.",
                suitability_score=0.0,
                preconditions_met=False,
                readiness=readiness,
                decision_explanation="Blocked: insufficient authorization or safety failure.",
                authorization=None,
            )

        # --- PLAN: generate workflow steps ---
        if not cognitive_decision.execution_allowed or auth is None:
            raise PlannerValidationError(
                "Planner received a PLAN action without execution authorization.",
                context={"decision_id": cognitive_decision.decision_id},
            )

        workflow = auth.workflow

        # Handle inherited intent from pending clarification
        health = cognitive_decision.cognitive_health
        if health.get("inherited_intent") and health.get("pending_intent"):
            workflow = IntentEngine.map_to_workflow_intent(health["pending_intent"])

        steps = _WORKFLOW_SEQUENCES.get(workflow, [])

        if not steps:
            # No valid sequence for this workflow — block
            return WorkflowPlan(
                steps=[],
                intent=workflow,
                reason=f"No agent sequence defined for workflow '{workflow}'.",
                suitability_score=0.0,
                preconditions_met=False,
                readiness=readiness,
                decision_explanation=f"No steps for workflow '{workflow}' — cannot execute.",
                authorization=auth,
            )

        readiness["suitability"] = round(intent_decision.confidence, 3)
        readiness["entities_ready"] = len(state.metadata.get("missing_critical", [])) == 0

        decision_str = (
            f"Workflow {workflow}: {len(steps)} agents. "
            f"Confidence {intent_decision.confidence:.3f}. "
            f"Authorization: {auth.decision_id}."
        )

        return WorkflowPlan(
            steps=steps,
            intent=workflow,
            reason=f"Executing {workflow} workflow.",
            suitability_score=round(intent_decision.confidence, 3),
            preconditions_met=True,
            readiness=readiness,
            decision_explanation=decision_str,
            authorization=auth,
        )


def select_workflow(state: WorkflowState) -> WorkflowPlan:
    """Module-level backward-compatible wrapper.

    This is called by the orchestrator. It runs the full cognitive pipeline
    internally to produce a WorkflowPlan.
    """
    from app.intents.intent_engine import IntentEngine as IE
    from app.engine.cognitive_engine import CognitiveEngine

    # Get the intent decision from state metadata (set by router)
    intent_decision = state.metadata.get("intent_decision")
    if intent_decision is None:
        # Fallback: re-classify (should not happen in normal flow)
        intent_decision = IE.classify_full(state.raw_input)
        state.metadata["intent_decision"] = intent_decision

    # Run cognitive engine
    cognitive = CognitiveEngine.decide(
        intent_decision,
        state.metadata,
        conversation_id=state.metadata.get("trace_id", ""),
    )
    state.metadata["cognitive_decision"] = cognitive
    state.metadata["cognitive_health"] = cognitive.cognitive_health

    # Generate plan
    return WorkflowPlanner.plan_from_decision(cognitive, state)
