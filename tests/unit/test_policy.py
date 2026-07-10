import unittest

from app.policy_engine import evaluate_policy, load_company_policy


class TestPolicyEngine(unittest.TestCase):
    def test_load_company_policy(self):
        policy = load_company_policy()
        self.assertIn("category_limits", policy)
        self.assertIn("restricted_vendors", policy)

    def test_standard_limit_meals(self):
        expense = {"merchant": "Pizza Hut", "category": "Meals", "amount": 45.00, "currency": "USD"}
        allowed, reimb, rej, violations, notes = evaluate_policy(expense, role="Associate")
        self.assertEqual(reimb, 45.00)
        self.assertEqual(rej, 0.0)
        self.assertEqual(len(violations), 0)

    def test_limit_exceeded_meals(self):
        expense = {"merchant": "Pizza Hut", "category": "Meals", "amount": 65.00, "currency": "USD"}
        allowed, reimb, rej, violations, notes = evaluate_policy(expense, role="Associate")
        self.assertEqual(reimb, 50.00)  # Capped at 50 USD
        self.assertEqual(rej, 15.00)
        self.assertTrue(any("Meals limit exceeded" in v or "limit exceeded" in v for v in violations))

    def test_restricted_vendor(self):
        expense = {"merchant": "Las Vegas Casino", "category": "Restricted", "amount": 120.00, "currency": "USD"}
        allowed, reimb, rej, violations, notes = evaluate_policy(expense, role="Associate")
        self.assertEqual(reimb, 0.0)
        self.assertEqual(rej, 120.00)
        self.assertTrue(any("Restricted Vendor" in v for v in violations))

    def test_role_multiplier_manager(self):
        expense = {"merchant": "Pizza Hut", "category": "Meals", "amount": 70.00, "currency": "USD"}
        # Manager limit is 50 * 1.5 = 75. So 70 is fully reimbursable.
        allowed, reimb, rej, violations, notes = evaluate_policy(expense, role="Manager")
        self.assertEqual(reimb, 70.00)
        self.assertEqual(rej, 0.0)

    def test_exception_conference_doubles_limit(self):
        expense = {"merchant": "Pizza Hut", "category": "Meals", "amount": 85.00, "currency": "USD"}
        # Limit doubled to 100 under conference exception.
        allowed, reimb, rej, violations, notes = evaluate_policy(
            expense, role="Associate", justification="Attended tech conference"
        )
        self.assertEqual(reimb, 85.00)
        self.assertEqual(rej, 0.0)

    def test_exception_executive_approval_unlimited(self):
        expense = {"merchant": "Gold Club Bar", "category": "Restricted", "amount": 250.00, "currency": "USD"}
        # Bypasses limits and restricted vendor blocks
        allowed, reimb, rej, violations, notes = evaluate_policy(
            expense, role="Associate", justification="CEO approved"
        )
        self.assertEqual(reimb, 250.00)
        self.assertEqual(rej, 0.0)
        self.assertEqual(len(violations), 0)
