import unittest
from app.fraud_detector import calculate_fraud_score, load_fraud_policy

class TestFraudDetector(unittest.TestCase):
    def test_load_fraud_policy(self):
        policy = load_fraud_policy()
        self.assertIn("weights", policy)
        self.assertIn("thresholds", policy)

    def test_no_fraud_anomalies(self):
        expense = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25", # Thursday
            "amount": 35.50,
            "currency": "USD"
        }
        score, reason = calculate_fraud_score(expense)
        self.assertEqual(score, 0)
        self.assertEqual(reason, "No suspicious anomalies detected.")

    def test_weekend_anomaly(self):
        expense = {
            "merchant": "Pizza Hut",
            "date": "2026-06-27", # Saturday
            "amount": 35.50,
            "currency": "USD"
        }
        score, reason = calculate_fraud_score(expense)
        self.assertEqual(score, 15)
        self.assertIn("weekend", reason.lower())

    def test_restricted_vendor(self):
        expense = {
            "merchant": "Gold Club Bar",
            "date": "2026-06-25",
            "amount": 35.50,
            "currency": "USD"
        }
        score, reason = calculate_fraud_score(expense)
        self.assertEqual(score, 40)
        self.assertIn("restricted", reason.lower())

    def test_duplicate_claims_history(self):
        expense = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25",
            "amount": 35.50,
            "currency": "USD"
        }
        history = [
            {"merchant": "Pizza Hut", "date": "2026-06-25", "amount": 35.50, "currency": "USD"}
        ]
        score, reason = calculate_fraud_score(expense, history=history)
        self.assertEqual(score, 30)
        self.assertIn("duplicate", reason.lower())

    def test_repeated_merchant_short_period(self):
        expense = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25",
            "amount": 35.50,
            "currency": "USD"
        }
        # Transaction 10 days prior
        history = [
            {"merchant": "Pizza Hut", "date": "2026-06-15", "amount": 35.50, "currency": "USD"}
        ]
        score, reason = calculate_fraud_score(expense, history=history)
        self.assertEqual(score, 15)
        self.assertIn("within 30 days", reason.lower())

    def test_just_under_review_threshold(self):
        expense = {
            "merchant": "Hilton Hotels",
            "date": "2026-06-25",
            "amount": 195.00, # Just below $200
            "currency": "USD"
        }
        score, reason = calculate_fraud_score(expense)
        self.assertEqual(score, 25)
        self.assertIn("threshold", reason.lower())

    def test_tampered_receipt_critical(self):
        expense = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25",
            "amount": 35.50,
            "currency": "USD",
            "manipulated_receipt": True
        }
        score, reason = calculate_fraud_score(expense)
        self.assertEqual(score, 60)
        self.assertTrue(any(w in reason.lower() for w in ["tampered", "manipulated", "edited"]))
