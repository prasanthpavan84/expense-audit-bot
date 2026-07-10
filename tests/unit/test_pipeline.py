import unittest
from datetime import datetime

from app.pipeline.decision import DecisionEngine
from app.pipeline.explain import ExplainabilityEngine
from app.pipeline.fraud import FraudEngine
from app.pipeline.parser import parse_expense
from app.pipeline.policy import PolicyEngine
from app.pipeline.validator import ValidationError, validate_expense


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.raw_data = {
            "employee_id": "EMP201",
            "merchant": "Uber",
            "amount": 25.00,
            "currency": "USD",
            "date": datetime.utcnow().isoformat(),
            "receipt_image": "dGVzdC1pbWFnZQ==",
        }

    def test_parser(self):
        expense = parse_expense(self.raw_data)
        self.assertEqual(expense.employee_id, "EMP201")
        self.assertEqual(expense.merchant, "Uber")
        self.assertEqual(expense.amount, 25.00)
        self.assertEqual(expense.currency, "USD")
        self.assertEqual(expense.receipt_image, "dGVzdC1pbWFnZQ==")

    def test_validator_valid(self):
        expense = parse_expense(self.raw_data)
        validated = validate_expense(expense)
        self.assertEqual(validated.employee_id, "EMP201")

    def test_validator_invalid_amount(self):
        data = self.raw_data.copy()
        data["amount"] = -10.0
        expense = parse_expense(data)
        with self.assertRaises(ValidationError):
            validate_expense(expense)

    def test_validator_invalid_currency(self):
        data = self.raw_data.copy()
        data["currency"] = "INVALID"
        expense = parse_expense(data)
        with self.assertRaises(ValidationError):
            validate_expense(expense)

    def test_fraud_engine(self):
        expense = parse_expense(self.raw_data)
        fraud_engine = FraudEngine()

        # Test duplicate
        history = [{"merchant": "Uber", "amount": 25.00, "date": self.raw_data["date"], "currency": "USD"}]
        res = fraud_engine.run(expense, history, 25.00)
        self.assertTrue(res.get("duplicate_receipt"))

        # Test normal
        res_normal = fraud_engine.run(expense, [], 25.0)
        self.assertFalse(res_normal.get("duplicate_receipt"))

    def test_policy_engine(self):
        expense = parse_expense(self.raw_data)
        policy_engine = PolicyEngine()
        res = policy_engine.evaluate(expense)
        self.assertTrue(res.get("within_limit"))

    def test_decision_engine(self):
        expense = parse_expense(self.raw_data)
        engine = DecisionEngine()
        decision = engine.run(expense)
        self.assertIn("audit_id", decision)
        self.assertIn("decision", decision)
        self.assertIn("confidence", decision)

    def test_explainability_engine(self):
        expense = parse_expense(self.raw_data)
        decision = {"audit_id": "test-uuid", "decision": "approved", "confidence": 1.0, "reasons": {}}
        engine = ExplainabilityEngine()
        explanation = engine.explain(decision, expense)
        self.assertEqual(explanation["audit_id"], "test-uuid")
        self.assertEqual(explanation["decision"], "approved")
        self.assertIn("approved", explanation["summary"].lower())
