import unittest
import os
import json
from app.query_engine import execute_query, load_database, save_database

class TestQueryEngine(unittest.TestCase):
    def setUp(self):
        # Backup existing database.json
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app", "database.json")
        self.backup_data = None
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                self.backup_data = json.load(f)
                
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
        with open(self.db_path, "w") as f:
            json.dump(self.test_data, f, indent=2)

    def tearDown(self):
        # Restore backup database
        if self.backup_data is not None:
            with open(self.db_path, "w") as f:
                json.dump(self.backup_data, f, indent=2)
        elif os.path.exists(self.db_path):
            os.remove(self.db_path)

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
