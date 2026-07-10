import unittest

from app.validation import (
    validate_currency,
    validate_date,
    validate_single_expense,
)


class TestValidationEngine(unittest.TestCase):
    def test_validate_date(self):
        # Valid date
        self.assertIsNone(validate_date("2026-06-25"))
        # Invalid date format
        self.assertIsNotNone(validate_date("25-06-2026"))
        self.assertIsNotNone(validate_date("2026/06/25"))
        # Invalid mathematical date (February 30th)
        self.assertIsNotNone(validate_date("2026-02-30"))
        # Future date check relative to 2026-06-30
        self.assertIsNotNone(validate_date("2026-07-01"))

    def test_validate_currency(self):
        self.assertIsNone(validate_currency("USD"))
        self.assertIsNone(validate_currency("INR"))
        self.assertIsNone(validate_currency("EUR"))
        self.assertIsNone(validate_currency("₹"))
        self.assertIsNone(validate_currency("$"))
        # Invalid currency format
        self.assertIsNotNone(validate_currency("US"))
        self.assertIsNotNone(validate_currency("US12"))

    def test_validate_single_expense_valid(self):
        exp = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25",
            "amount": 35.50,
            "currency": "USD",
            "category": "Meals",
            "items_list": [],
        }
        errors = validate_single_expense(exp, "Pizza Hut bill $35.50 on 2026-06-25")
        self.assertEqual(len(errors), 0)

    def test_validate_single_expense_negative_amount(self):
        exp = {"merchant": "Pizza Hut", "date": "2026-06-25", "amount": -10.00, "currency": "USD", "category": "Meals"}
        errors = validate_single_expense(exp, "Pizza Hut bill $-10.00")
        self.assertTrue(any("positive" in err for err in errors))

    def test_validate_single_expense_zero_amount(self):
        exp = {"merchant": "Pizza Hut", "date": "2026-06-25", "amount": 0.0, "currency": "USD", "category": "Meals"}
        errors = validate_single_expense(exp, "Pizza Hut bill $0.0")
        self.assertTrue(any("zero" in err for err in errors))

    def test_validate_single_expense_excessive_amount(self):
        exp = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25",
            "amount": 1000001.00,
            "currency": "USD",
            "category": "Meals",
        }
        errors = validate_single_expense(exp, "Pizza Hut bill $1,000,001.00")
        self.assertTrue(any("limit" in err for err in errors))

    def test_arithmetic_validation(self):
        exp = {
            "merchant": "Pizza Hut",
            "date": "2026-06-25",
            "amount": 40.0,
            "currency": "USD",
            "category": "Meals",
            "items_list": [
                {"name": "Pizza", "amount": 25.0, "category": "Meals"},
                {"name": "Soda", "amount": 10.0, "category": "Meals"},
            ],
        }
        # Total amount is 40.0, but sum of items is 35.0. Should error.
        errors = validate_single_expense(exp, "Pizza Hut total $40.00")
        self.assertTrue(any("mismatch" in err for err in errors))

    def test_hallucination_check(self):
        exp = {"merchant": "McDonalds", "date": "2026-06-25", "amount": 45.0, "currency": "USD", "category": "Meals"}
        # McDonalds is not in the text, should flag as hallucinated
        errors = validate_single_expense(exp, "Pizza Hut total $45.00 on 2026-06-25")
        self.assertTrue(any("hallucination" in err or "not found" in err for err in errors))

    def test_duplicate_check_history(self):
        exp = {"merchant": "Pizza Hut", "date": "2026-06-25", "amount": 35.50, "currency": "USD", "category": "Meals"}
        history = [{"merchant": "Pizza Hut", "date": "2026-06-25", "amount": 35.50, "currency": "USD"}]
        errors = validate_single_expense(exp, "Pizza Hut total $35.50 on 2026-06-25", history=history)
        self.assertTrue(any("Duplicate" in err for err in errors))
