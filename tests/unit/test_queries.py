import unittest
import os
import json
from app.query_engine import execute_query, load_database, save_database

class TestQueryEngine(unittest.TestCase):
    def setUp(self):
        # Set database path to a separate temporary test file
        self.test_db_path = os.path.join(os.path.dirname(__file__), "test_database.json")
        os.environ["DATABASE_PATH"] = self.test_db_path
                
        # Setup temporary test database content
        self.test_data = [
            {
                "id": "t-001",
                "employee_id": "EMP201",
                "department": "Engineering",
                "merchant": "Uber",
                "date": "2026-06-15",
                "amount": 25.0,
                "currency": "USD",
                "category": "Taxi",
                "status": "Approved",
                "fraud_score": 10
            },
            {
                "id": "t-002",
                "employee_id": "EMP201",
                "department": "Engineering",
                "merchant": "Hilton Hotels",
                "date": "2026-06-16",
                "amount": 220.0,
                "currency": "USD",
                "category": "Hotel",
                "status": "Approved with Exception",
                "fraud_score": 20
            },
            {
                "id": "t-003",
                "employee_id": "EMP202",
                "department": "Sales",
                "merchant": "Pizza Hut",
                "date": "2026-06-15",
                "amount": 40.0,
                "currency": "USD",
                "category": "Meals",
                "status": "Approved",
                "fraud_score": 5
            },
            {
                "id": "t-004",
                "employee_id": "EMP202",
                "department": "Sales",
                "merchant": "Gold Club Bar",
                "date": "2026-06-17",
                "amount": 80.0,
                "currency": "USD",
                "category": "Restricted",
                "status": "Rejected",
                "fraud_score": 50
            }
        ]
        with open(self.test_db_path, "w") as f:
            json.dump(self.test_data, f, indent=2)

    def tearDown(self):
        # Remove temporary test database file and clean env variable
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]

    def test_filter_by_category(self):
        query = {
            "action": "FILTER",
            "category": "Taxi"
        }
        res = execute_query(query)
        self.assertEqual(res["summary"]["total_count"], 1)
        self.assertEqual(res["data"][0]["merchant"], "Uber")

    def test_filter_by_amount_min(self):
        query = {
            "action": "FILTER",
            "amount_min": 100.0
        }
        res = execute_query(query)
        self.assertEqual(res["summary"]["total_count"], 1)
        self.assertEqual(res["data"][0]["id"], "t-002")

    def test_compare_departments(self):
        query = {
            "action": "COMPARE_DEPTS"
        }
        res = execute_query(query)
        # We expect Engineering and Sales comparisons
        depts = [item["department"] for item in res["data"]]
        self.assertIn("Engineering", depts)
        self.assertIn("Sales", depts)

    def test_summarize_employee(self):
        query = {
            "action": "SUMMARIZE_EMPLOYEE",
            "employee_id": "EMP201"
        }
        res = execute_query(query)
        self.assertEqual(res["data"]["total_claims"], 2)
        self.assertEqual(res["data"]["total_claimed"], 245.0)

    def test_explain_rejected_expense(self):
        query = {
            "action": "EXPLAIN",
            "target_expense_id": "t-004"
        }
        res = execute_query(query)
        self.assertEqual(res["data"]["merchant"], "Gold Club Bar")
        self.assertEqual(res["data"]["status"], "Rejected")
