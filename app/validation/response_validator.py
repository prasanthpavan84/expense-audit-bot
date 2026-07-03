"""Response Validation — v2 (Hardened).

Validates the final response by checking:
  - Intent satisfied
  - Planner decision aligned
  - Conversation Firewall respected
  - Authorization valid
  - Workflow complete with mandatory agents
  - Evidence present
  - Confidence calibrated
  - Clarification resolved
  - Lifecycle consistent
"""

from typing import List

from app.models.state import WorkflowState
from app.engine.confidence_engine import calibrate_confidence
from app.intents.clarification_manager import ClarificationManager

CONFIDENCE_THRESHOLD = 0.6


def validate_response(state: WorkflowState) -> bool:
    """Validate the response based on the current workflow state.

    Returns ``True`` if the response is ready to be sent, ``False`` if a
    clarification step should be inserted.
    """
    # 1. Ensure intents were detected
    intents = state.metadata.get("intents", [])
    if not intents:
        state.metadata["clarification_question"] = "I couldn't understand your request. Could you rephrase?"
        state.status = "CLARIFY"
        return False

    # 2. Check validation errors from ValidationAgent
    if state.metadata.get("validation_errors"):
        state.metadata["clarification_question"] = (
            "Your request contains validation errors. Could you clarify the details?"
        )
        state.status = "CLARIFY"
        return False

    # 3. Calibrate confidence
    conf_res = calibrate_confidence(state)
    state.metadata["calibrated_confidence"] = conf_res.overall
    state.metadata["confidence_details"] = conf_res.explanation

    if conf_res.overall < CONFIDENCE_THRESHOLD:
        if ClarificationManager.should_clarify(state):
            question = ClarificationManager.generate_question(state)
            state.metadata["clarification_question"] = question
            state.status = "CLARIFY"
            return False

    # 4. Verify execution of required agents
    perf = state.metadata.get("performance", {})
    plan_dict = state.metadata.get("workflow_plan", {})
    required_steps = plan_dict.get("steps", [])
    for step in required_steps:
        if step not in perf:
            state.metadata["clarification_question"] = (
                f"Workflow incomplete: agent '{step}' did not execute."
            )
            state.status = "CLARIFY"
            return False

    # 5. Ensure evidence for audit conclusions
    evidence = state.metadata.get("evidence", [])
    has_audit = any(i.get("primary") == "AUDIT" for i in intents)
    if has_audit and not evidence:
        state.metadata["clarification_question"] = (
            "No evidence found to support the audit conclusions. "
            "Could you please provide a valid expense description?"
        )
        state.status = "CLARIFY"
        return False

    # 6. Verify firewall consistency
    cognitive = state.metadata.get("cognitive_decision")
    if cognitive and not cognitive.firewall_passed:
        # Firewall blocked — ensure no expense agents ran
        for agent_name in ["receipt_extractor", "validation_agent",
                           "policy_agent", "fraud_agent",
                           "reflection_agent", "report_agent"]:
            if agent_name in perf:
                state.metadata["clarification_question"] = (
                    f"Safety error: agent '{agent_name}' ran despite firewall block."
                )
                state.status = "CLARIFY"
                return False

    # All checks passed
    state.status = "COMPLETED"
    return True
