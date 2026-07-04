"""Comprehensive unit test suite for the AI Intelligence Hardening layer (Volume 7.5)."""

import asyncio
import unittest
from app.models.state import WorkflowState, ExpenseItem, AuditResult
from app.intents.intent_engine import IntentEngine, IntentResult
from app.intents.nlu import NLU, NLUResult
from app.intents.context_manager import ContextManager, ConversationContext
from app.intents.multi_intent import MultiIntentDetector
from app.workflows.planner import WorkflowPlanner, select_workflow
from app.workflows.orchestrator import WorkflowOrchestrator
from app.models.evidence import EvidenceCollector
from app.engine.confidence_engine import ConfidenceCalibrationEngine
from app.agents.reflection_agent import ReflectionAgent
from app.agents.hallucination_agent import HallucinationAgent
from app.intents.clarification_manager import ClarificationManager
from app.validation.response_validator import validate_response



class TestAIIntelligence(unittest.TestCase):
    """Test suite covering the 12 cognitive subsystems of Volume 7.5."""

    # 1. Intent Classification tests
    def test_intent_classification(self):
        test_cases = [
            ("hello", "GREETING"),
            ("goodbye", "FAREWELL"),
            ("what can you do", "HELP"),
            ("upload receipt here is the bill", "RECEIPT_UPLOAD"),
            ("audit this expense report", "AUDIT"),
            ("what is the company limit for meals?", "POLICY"),
            ("calculate total reimbursement", "FINANCIAL"),
            ("duplicate fake suspicious receipt", "FRAUD"),
            ("validate correct format", "VALIDATION"),
            ("generate a CSV report for me", "REPORT"),
            ("why did my hotel expense fail?", "FOLLOW_UP"),
            ("and also add this to the total", "FOLLOW_UP"),
            ("what is definition of flight rules", "GENERAL_KNOWLEDGE"),
            ("play some music on spotify", "UNKNOWN"),
        ]
        for text, expected_intent in test_cases:
            res = IntentEngine.classify_full(text)
            self.assertEqual(res.stage2_intent, expected_intent, f"Failed for text: {text}")
            self.assertTrue(0.0 <= res.confidence <= 1.0)
            self.assertIsNotNone(res.decision_id)

    # 2. Ambiguity Detection test
    def test_ambiguity_detection(self):
        # Text matching keywords from both GREETING and HELP or AUDIT
        ambiguous_text = "hello, please audit this for me or tell me what is policy"
        res = IntentEngine.classify_full(ambiguous_text)
        # Should detect competing intents and flag for clarification if confident enough, or drop to UNKNOWN
        self.assertTrue(res.requires_clarification or res.stage2_intent == "UNKNOWN")

    # 3. Entity Extraction tests
    def test_entity_extraction(self):
        text = "I spent $150.50 at Hilton on 2026-06-25 as a manager for employee EMP404 in engineering"
        res = NLU.extract_entities(text)
        
        self.assertIn(150.50, res.entities["amounts"])
        self.assertEqual(res.entities["currency"], "USD")
        self.assertEqual(res.entities["date"], "2026-06-25")
        self.assertEqual(res.entities["merchant"], "Hilton")
        self.assertEqual(res.entities["category"], "Hotel")
        self.assertEqual(res.entities["department"], "Engineering")
        self.assertEqual(res.entities["employee_id"], "EMP404")
        self.assertEqual(res.user_role, "manager")
        self.assertEqual(res.context_type, "expense_submission")

    # 4. Critical vs Optional fields classification
    def test_critical_vs_optional_classification(self):
        # Audit intent: requires amount and merchant
        res_audit = NLUResult(entities={"amount": 100})  # missing merchant
        NLU.classify_missing_fields(res_audit, "AUDIT")
        self.assertIn("merchant", res_audit.missing_critical)
        self.assertNotIn("amount", res_audit.missing_critical)
        self.assertIn("date", res_audit.missing_optional)

        # Policy intent: requires policy reference
        res_policy = NLUResult(entities={})
        NLU.classify_missing_fields(res_policy, "POLICY")
        self.assertIn("policy_reference", res_policy.missing_critical)

    # 5. Multi-Intent Detection & Prioritization
    def test_multi_intent_detection(self):
        text = "Hi, check this suspicious receipt and explain the policy violation"
        res = MultiIntentDetector.detect_all_intents(text)
        
        # Should detect GREETING, AUDIT, FRAUD, POLICY
        intents = [r.intent for r in res]
        self.assertIn("POLICY", intents)
        self.assertIn("GREETING", intents)

    # 6. Workflow Selection, Preconditions, and Suitability
    def test_workflow_selection(self):
        # Post-clarification: Set state to ACTIVE, missing fields provided
        state = WorkflowState(raw_input="audit this for Uber $25")
        state.status = "ACTIVE"
        ContextManager.transition_to(state, "ACTIVE")
        state.metadata["missing_critical"] = []
        state.metadata["nlu_entities"] = {"merchant": "Uber", "amount": 25.0}
        
        from app.intents.intent_engine import IntentDecision
        from app.intents.preprocessors.input_classifier import InputType
        state.metadata["intent_decision"] = IntentDecision(
            decision_id="mock",
            raw_input="audit this expense report",
            normalized_input="audit this expense report",
            input_type=InputType.CHAT,
            stage1_category="Expense",
            stage2_intent="AUDIT",
            confidence=0.95,
            requires_clarification=False,
            planner_permission=True,
            confidence_breakdown={},
            negative_matches=(),
            classifier_votes=(),
            reason="mock",
            timestamp="2026-07-02T12:00:00"
        )
        
        plan2 = select_workflow(state)
        self.assertTrue(plan2.preconditions_met)
        self.assertTrue(len(plan2.steps) > 0)
        
        # Case B: Correct steps
        state = WorkflowState(raw_input="audit $150 at Hilton")
        state.intent = "AUDIT"
        state.metadata["intent_confidence"] = 1.0
        state.metadata["nlu_entities"] = {"amount": 150.0, "merchant": "Hilton"}
        state.metadata["missing_critical"] = []
        state.metadata["intent_decision"] = IntentDecision(
            decision_id="mock",
            raw_input="audit $150 at Hilton",
            normalized_input="audit $150 at Hilton",
            input_type=InputType.CHAT,
            stage1_category="Expense",
            stage2_intent="AUDIT",
            confidence=1.0,
            requires_clarification=False,
            planner_permission=True,
            confidence_breakdown={},
            negative_matches=(),
            classifier_votes=(),
            reason="mock",
            timestamp="2026-07-02T12:00:00"
        )
        
        plan = select_workflow(state)
        self.assertTrue(plan.preconditions_met)
        self.assertIn("receipt_extractor", plan.steps)
        self.assertIn("reflection_agent", plan.steps)

    # 7. Conversation Firewall
    def test_conversation_firewall(self):
        state = WorkflowState(raw_input="hello, good morning")
        state.intent = "CONVERSATION"
        state.metadata["intent_decision"] = IntentEngine.classify_full("hello, good morning")
        
        plan = select_workflow(state)
        self.assertEqual(len(plan.steps), 0)
        self.assertEqual(plan.intent, "CONVERSATION")
        self.assertIn("Conversation firewall", plan.decision_explanation)

    # 8. Conversation Lifecycle State progress
    def test_conversation_lifecycle(self):
        state = WorkflowState(raw_input="Audit $150 Hilton")
        state.metadata["nlu_entities"] = {"amount": 150.0, "merchant": "Hilton"}
        
        ContextManager.update(state)
        ctx = ContextManager.get_or_create_context(state)
        self.assertEqual(ctx.lifecycle_state, "ACTIVE")
        
        # Valid state jump: ACTIVE -> CLARIFYING
        success = ContextManager.transition_to(state, "CLARIFYING")
        self.assertTrue(success)
        
        # Invalid state jump: CLARIFYING -> STARTED (violates matrix)
        success = ContextManager.transition_to(state, "STARTED")
        self.assertFalse(success)
        ctx = ContextManager.get_or_create_context(state)
        self.assertEqual(ctx.lifecycle_state, "CLARIFYING")

    # 9. Safety Guard: Recursive loop prevention
    def test_recursive_loop_prevention(self):
        state = WorkflowState(raw_input="audit empty receipt")
        state.metadata["missing_critical"] = ["amount", "merchant"]
        state.metadata["calibrated_confidence"] = 0.3
        
        # Attempt clarification multiple times
        questions = []
        for _ in range(4):
            q = ClarificationManager.generate_question(state)
            questions.append(q)
            
        self.assertEqual(
            questions[-1], 
            "I wasn't able to gather enough information after multiple attempts. Please provide the complete details and try again."
        )

    # 10. Reflection Validation
    def test_reflection_validation(self):
        state = WorkflowState(raw_input="Audit $150 hotel stay")
        exp = ExpenseItem(merchant="Hilton", amount=150.0, currency="USD", confidence_score=0.9)
        state.expenses.append(exp)
        
        # Setup audit result with contradiction (approved but has violation)
        res = AuditResult(is_approved=True, policy_violations=["Hotel limit exceeded"])
        state.audit_results["expense_0"] = res
        state.metadata["policy_checks"] = {"Hotel limit exceeded": True}
        state.metadata["fraud_indicators"] = ["High risk vendor"]
        
        # Run reflection agent
        agent = ReflectionAgent()
        asyncio.run(agent.process_state(state))
        
        # Reflection should detect the contradiction
        self.assertIn("[CONTRADICTION]", res.reasoning_trace)
        self.assertIn("[NEEDS_EVIDENCE]", res.reasoning_trace)
        self.assertFalse(state.metadata["reflection_results"]["expense_0"]["has_unsupported"])
        self.assertTrue(state.metadata["reflection_results"]["expense_0"]["has_contradictions"])

    # 11. Hallucination Prevention
    def test_hallucination_prevention(self):
        state = WorkflowState(raw_input="Audit $150 stay at Hilton")
        # Extract fabricated merchant (not in raw text)
        exp = ExpenseItem(merchant="Starbucks", amount=150.0, currency="USD")
        state.expenses.append(exp)
        
        agent = HallucinationAgent()
        asyncio.run(agent.process_state(state))
        
        self.assertEqual(exp.confidence_score, 0.1)
        self.assertTrue(state.metadata["hallucinations_detected"])
        self.assertIn("hallucinations", state.metadata)

    # 12. Confidence Calibration
    def test_confidence_calibration(self):
        state = WorkflowState(raw_input="Audit $150 Hilton")
        state.metadata["intent_confidence"] = 1.0
        state.metadata["nlu_entities"] = {"amount": 150.0, "merchant": "Hilton"}
        
        # Normal case
        res = ConfidenceCalibrationEngine.calibrate_confidence(state)
        self.assertTrue(res.overall >= 0.8)
        
        # Case with validation errors and missing critical fields
        state.metadata["validation_errors"] = ["Format invalid"]
        state.metadata["missing_critical"] = ["date"]
        res_penalized = ConfidenceCalibrationEngine.calibrate_confidence(state)
        
        # Penalties: -0.2 for validation errors, -0.15 for missing critical fields
        self.assertTrue(res_penalized.overall < res.overall)
        self.assertTrue(len(res_penalized.penalties) >= 2)

    # 13. End-to-end Orchestrator integration
    def test_orchestrator_integration(self):
        orchestrator = WorkflowOrchestrator()
        
        # Greetings should never trigger receipt workflows and should return response directly
        state = asyncio.run(orchestrator.run("hello there"))
        self.assertEqual(state.status, "COMPLETED")
        self.assertEqual(state.metadata.get("response"), "Hello! I am your Expense Audit assistant. How can I help you today?")
        
        # Missing critical info triggers clarification
        state_clarify = asyncio.run(orchestrator.run("please audit this receipt"))
        self.assertEqual(state_clarify.status, "CLARIFY")
        self.assertIn("clarification_question", state_clarify.metadata)
        
    # 14. Post-clarification re-planning
    def test_post_clarification_replanning(self):
        orchestrator = WorkflowOrchestrator()
        
        # Step 1: User says "audit this" -> fails precondition -> context stores pending_clarification_intent="AUDIT"
        state = asyncio.run(orchestrator.run("please audit this"))
        self.assertEqual(state.status, "CLARIFY")
        
        # Retrieve context dictionary
        ctx_dict = state.metadata["context"]
        self.assertEqual(ctx_dict["pending_clarification_intent"], "AUDIT")
        
        # Step 2: User provides details -> planner picks up pending_intent="AUDIT" -> executes audit from scratch
        # Enrich metadata with the context dictionary to simulate conversation turn
        state2 = WorkflowState(raw_input="it is $150 at Hilton")
        state2.metadata["context"] = ctx_dict
        
        # Run orchestrator passing state2 to preserve context
        state2 = asyncio.run(orchestrator.run("it is $150 at Hilton", state2))
        # Since it is a new run without mocked DB/file, it will run extractor/reflection
        # and validate response (which might ask for evidence, but we verify it planned the steps!)
        plan_dict = state2.metadata.get("workflow_plan", {})
        self.assertEqual(plan_dict.get("intent"), "AUDIT")
        self.assertIn("receipt_extractor", plan_dict.get("steps", []))


if __name__ == "__main__":
    unittest.main()
