"""Cognitive Decision Engine — the central decision-maker of the cognitive pipeline.

Sits between Intent Engine / Context Manager and the Planner.
Responsibilities:
  - Merge intent and context
  - Decide whether clarification is needed
  - Apply conversation firewall
  - Determine if execution is allowed
  - Produce the final ``CognitiveDecision`` for the planner

The Planner SHALL NOT classify intent, override intent, infer user goals,
request clarification, or perform safety decisions.

Core principle: THE AI MUST NEVER GUESS.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from app.intents.intent_engine import IntentDecision, IntentEngine, CONVERSATION_INTENTS
from app.engine.exceptions import ConversationFirewallViolation


# ---------------------------------------------------------------------------
# Immutable Decision Objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionAuthorization:
    """Immutable token required before any expense agent can run."""
    decision_id: str
    conversation_id: str
    workflow_id: str
    permission: bool
    reason: str
    issued_by: str  # always "cognitive_engine"
    timestamp: str
    expires: str
    workflow: str  # "AUDIT", "POLICY", etc.


@dataclass(frozen=True)
class CognitiveDecision:
    """Immutable cognitive decision — single source of truth for the planner."""
    decision_id: str
    intent: IntentDecision
    context_ready: bool
    clarification_required: bool
    clarification_reason: str
    execution_allowed: bool
    authorization: Optional[ExecutionAuthorization]
    safety_checks_passed: bool
    firewall_passed: bool
    next_action: str  # "PLAN", "CLARIFY", "RESPOND", "BLOCK"
    planner_permission: bool
    cognitive_health: Dict[str, Any]


# Conversation intents that MUST NEVER trigger expense workflows
_FIREWALL_BLOCKED_INTENTS = CONVERSATION_INTENTS | frozenset({
    "RESTART", "CANCEL",
})

# Expense agent names — the firewall protects these from conversational intents
_EXPENSE_AGENTS = frozenset({
    "receipt_extractor", "validation_agent", "policy_agent",
    "fraud_agent", "reflection_agent", "report_agent",
})


class CognitiveEngine:
    """The central cognitive decision-maker.

    Pipeline position: Intent Engine → Context Manager → **Cognitive Engine** → Planner
    """

    @staticmethod
    def decide(
        intent_decision: IntentDecision,
        state_metadata: Dict[str, Any],
        conversation_id: str = "",
    ) -> CognitiveDecision:
        """Produce an immutable ``CognitiveDecision``.

        Parameters
        ----------
        intent_decision : IntentDecision
            The immutable intent classification result.
        state_metadata : dict
            Current workflow state metadata (entities, context, etc.).
        conversation_id : str
            Conversation ID for tracing.
        """
        decision_id = intent_decision.decision_id
        stage2 = intent_decision.stage2_intent
        confidence = intent_decision.confidence

        # --- 1. Conversation Firewall ---
        firewall_passed = stage2 not in _FIREWALL_BLOCKED_INTENTS
        firewall_reason = ""
        if not firewall_passed:
            firewall_reason = (
                f"Conversation Firewall: intent '{stage2}' is blocked from expense workflows. "
                f"Blocked agents: {sorted(_EXPENSE_AGENTS)}"
            )

        # --- 2. Context readiness ---
        context = state_metadata.get("context", {})
        pending_intent = None
        if isinstance(context, dict):
            pending_intent = context.get("pending_clarification_intent")
        context_ready = bool(context)

        # --- 3. Intent stability: inherit pending intent for tiny replies ---
        inherited_intent = False
        if (
            pending_intent
            and pending_intent not in _FIREWALL_BLOCKED_INTENTS
            and stage2 in ("CONTINUE", "FOLLOW_UP", "UNKNOWN")
        ):
            # The user's reply should continue the pending workflow
            inherited_intent = True
            # We don't mutate intent_decision (it's frozen), but we signal
            # to the planner that the pending intent should be used.
            firewall_passed = True  # pending intent was already approved

        # --- 4. Clarification logic ---
        # If we inherited the intent, we don't care about the low confidence of the current reply
        clarification_required = intent_decision.requires_clarification if not inherited_intent else False
        clarification_reason = ""

        if clarification_required:
            if confidence < 0.55:
                clarification_reason = "Confidence too low — request rephrase"
            elif intent_decision.stage2_intent == "UNKNOWN":
                clarification_reason = "Intent could not be determined — please rephrase"
            else:
                clarification_reason = "Ambiguous intent — please clarify"

        # Missing critical entities for expense intents
        missing_critical = state_metadata.get("missing_critical", [])
        if firewall_passed and not clarification_required and missing_critical:
            clarification_required = True
            clarification_reason = f"Missing critical fields: {', '.join(missing_critical)}"

        # --- 5. Safety checks ---
        safety_passed = True
        if not firewall_passed and stage2 not in _FIREWALL_BLOCKED_INTENTS:
            safety_passed = False

        # --- 6. Execution allowed? ---
        execution_allowed = (
            firewall_passed
            and not clarification_required
            and safety_passed
            and (intent_decision.planner_permission or inherited_intent)
        )

        # --- 7. Build authorization token ---
        authorization = None
        if execution_allowed:
            workflow = IntentEngine.map_to_workflow_intent(
                pending_intent if inherited_intent else stage2
            )
            authorization = ExecutionAuthorization(
                decision_id=decision_id,
                conversation_id=conversation_id or str(uuid.uuid4()),
                workflow_id=str(uuid.uuid4()),
                permission=True,
                reason=f"Approved: intent={stage2}, confidence={confidence:.3f}",
                issued_by="cognitive_engine",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                expires=time.strftime("%Y-%m-%dT%H:%M:%S"),  # expires immediately for single-use
                workflow=workflow,
            )

        # --- 8. Determine next action ---
        if not firewall_passed:
            next_action = "RESPOND"  # conversational → direct response
        elif clarification_required:
            next_action = "CLARIFY"
        elif execution_allowed:
            next_action = "PLAN"
        else:
            next_action = "BLOCK"

        # --- 9. Cognitive health metrics ---
        health = {
            "intent_confidence": confidence,
            "entity_confidence": state_metadata.get("nlu_entities_confidence", 0.0),
            "conversation_confidence": intent_decision.confidence_breakdown.get("conversation", 0.0),
            "planner_confidence": confidence if execution_allowed else 0.0,
            "firewall_decision": "PASS" if firewall_passed else "BLOCK",
            "firewall_reason": firewall_reason,
            "clarification_count": state_metadata.get("clarification_session", {}).get("retry_count", 0),
            "workflow_block_reason": clarification_reason if not execution_allowed else "",
            "safety_checks_passed": safety_passed,
            "inherited_intent": inherited_intent,
            "pending_intent": pending_intent,
        }

        return CognitiveDecision(
            decision_id=decision_id,
            intent=intent_decision,
            context_ready=context_ready,
            clarification_required=clarification_required,
            clarification_reason=clarification_reason,
            execution_allowed=execution_allowed,
            authorization=authorization,
            safety_checks_passed=safety_passed,
            firewall_passed=firewall_passed,
            next_action=next_action,
            planner_permission=execution_allowed,
            cognitive_health=health,
        )

    @staticmethod
    def validate_firewall(intent: str, agent_name: str) -> None:
        """Raise ``ConversationFirewallViolation`` if a blocked intent
        tries to execute an expense agent.

        Call this inside the orchestrator before each agent execution.
        """
        if intent in _FIREWALL_BLOCKED_INTENTS and agent_name in _EXPENSE_AGENTS:
            raise ConversationFirewallViolation(
                f"FIREWALL VIOLATION: intent '{intent}' attempted to execute "
                f"expense agent '{agent_name}'",
                context={"intent": intent, "agent": agent_name},
            )
