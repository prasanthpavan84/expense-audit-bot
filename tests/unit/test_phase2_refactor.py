import unittest

from core.container.service_container import ServiceContainer
from core.event_bus import EventBus
from core.llm.model_manager import ModelManager
from core.memory.shared_memory import SharedMemory
from core.runtime.state_manager import (
    InvalidStateTransitionError,
    RuntimeState,
    StateManager,
)
from domain.receipt import Receipt
from use_cases.audit_expense import AuditExpenseUseCase
from use_cases.validate_receipt import ValidateReceiptUseCase


class TestPhase2Refactor(unittest.TestCase):

    def setUp(self):
        # Setup common service container
        self.services = ServiceContainer(
            event_bus=EventBus(),
            memory=SharedMemory(),
            llm_manager=ModelManager(),
        )

    def test_service_container(self):
        self.assertIsNotNone(self.services.event_bus)
        self.assertIsNotNone(self.services.memory)
        self.assertIsNotNone(self.services.llm_manager)

    def test_state_manager_transitions(self):
        state_mgr = StateManager()
        self.assertEqual(state_mgr.current_state, RuntimeState.CREATED)

        # Valid transitions
        state_mgr.transition_to(RuntimeState.READY)
        self.assertEqual(state_mgr.current_state, RuntimeState.READY)

        state_mgr.transition_to(RuntimeState.RUNNING)
        self.assertEqual(state_mgr.current_state, RuntimeState.RUNNING)

        state_mgr.transition_to(RuntimeState.FINISHED)
        self.assertEqual(state_mgr.current_state, RuntimeState.FINISHED)

        # Invalid transition from terminal state
        with self.assertRaises(InvalidStateTransitionError):
            state_mgr.transition_to(RuntimeState.RUNNING)

    def test_validate_receipt_use_case(self):
        use_case = ValidateReceiptUseCase(self.services)
        # Test basic success case
        raw_input = "Uber ride expense of $12.50 on 2026-06-25"
        result = use_case.execute(raw_input)

        self.assertEqual(result.status, "COMPLETED")
        self.assertIsInstance(result.output, Receipt)
        self.assertEqual(result.output.merchant_name, "Taxi ride")
        self.assertEqual(result.output.amount, 12.50)
        self.assertEqual(result.output.currency, "USD")
        self.assertEqual(result.output.date, "2026-06-25")

    def test_audit_expense_use_case_success(self):
        use_case = AuditExpenseUseCase(self.services)
        raw_input = "Meals at Starbucks for $15.00 on 2026-06-25"
        result = use_case.execute(raw_input)

        self.assertEqual(result.status, "COMPLETED")
        self.assertIsNotNone(result.output)
        self.assertEqual(result.output.status, "APPROVED")
        self.assertTrue(len(result.trace) > 0)

    def test_audit_expense_use_case_violation(self):
        use_case = AuditExpenseUseCase(self.services)
        # Hilton limit is $150, so $200 should violate limits and fail compliance
        raw_input = "Hotel stay at Hilton for $200.00 on 2026-06-25"
        result = use_case.execute(raw_input)

        self.assertEqual(result.status, "FAILED")
        self.assertIsNotNone(result.output)
        self.assertEqual(result.output.status, "REJECTED")
        self.assertTrue(
            any("violation" in t.decision.lower() or "evaluated" in t.decision.lower() for t in result.trace)
        )
