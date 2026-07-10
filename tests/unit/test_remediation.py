# Copyright 2026 Google LLC
# Remediation regression tests

import json
import os
import threading

import pytest

# Use temporary database path for tests
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DB_PATH = os.path.join(PROJECT_DIR, "tests", "unit", "temp_remediation_db.json")
os.environ["DATABASE_PATH"] = TEMP_DB_PATH

from app.agent import finalize_expense, route_decision
from app.query_engine import add_expense_to_db, execute_query, load_database


class MockContext:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = {}
        self.resume_inputs = {}

    @property
    def session(self):
        class SessionStub:
            id = self.session_id

        return SessionStub()


@pytest.fixture(autouse=True)
def clean_db():
    old_db_path = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = TEMP_DB_PATH
    with open(TEMP_DB_PATH, "w") as f:
        json.dump([], f)
    yield
    if os.path.exists(TEMP_DB_PATH):
        try:
            os.remove(TEMP_DB_PATH)
        except Exception:
            pass
    if old_db_path is not None:
        os.environ["DATABASE_PATH"] = old_db_path
    elif "DATABASE_PATH" in os.environ:
        del os.environ["DATABASE_PATH"]


def test_route_decision_needs_review_normalization():
    """Verify route_decision correctly routes Needs Human Review variants to needs_review."""
    # Test variant 1: Needs Human Review
    ctx1 = MockContext("s1")
    ctx1.state["orchestrator_decision"] = "Needs Human Review"
    evt1 = route_decision(ctx1, "Input text")
    assert evt1.actions.route == "needs_review"

    # Test variant 2: needs_review
    ctx2 = MockContext("s2")
    ctx2.state["orchestrator_decision"] = "needs_review"
    evt2 = route_decision(ctx2, "Input text")
    assert evt2.actions.route == "needs_review"

    # Test variant 3: Needs Review
    ctx3 = MockContext("s3")
    ctx3.state["orchestrator_decision"] = "Needs Review"
    evt3 = route_decision(ctx3, "Input text")
    assert evt3.actions.route == "needs_review"


def test_route_decision_denied_normalization():
    """Verify route_decision correctly routes Denied / Rejected variants to denied."""
    ctx1 = MockContext("s1")
    ctx1.state["orchestrator_decision"] = "Rejected"
    evt1 = route_decision(ctx1, "Input text")
    assert evt1.actions.route == "denied"

    ctx2 = MockContext("s2")
    ctx2.state["orchestrator_decision"] = "Denied"
    evt2 = route_decision(ctx2, "Input text")
    assert evt2.actions.route == "denied"


def test_route_decision_approved_normalization():
    """Verify route_decision correctly routes Approved variants to approved."""
    ctx1 = MockContext("s1")
    ctx1.state["orchestrator_decision"] = "Approved"
    evt1 = route_decision(ctx1, "Input text")
    assert evt1.actions.route == "approved"

    ctx2 = MockContext("s2")
    ctx2.state["orchestrator_decision"] = "Approved with Exception"
    evt2 = route_decision(ctx2, "Input text")
    assert evt2.actions.route == "approved"


def test_partially_approved_persistence():
    """Verify Partially Approved expenses are successfully saved, retrieved, and queried."""
    ctx = MockContext("s_partial")
    ctx.state["audited_expenses"] = [
        {
            "merchant": "Hilton Hotels",
            "date": "2026-06-26",
            "amount": 280.00,
            "currency": "USD",
            "category": "Hotel",
            "reimbursable": 150.0,
            "rejected": 130.0,
            "fraud_score": 10,
            "fraud_reason": "Low risk",
            "status": "Partially Approved",
            "ocr_confidence_score": 1.0,
            "manipulated_receipt": False,
            "employee_id": "EMP102",
            "department": "Engineering",
        }
    ]

    # Run finalize_expense node (yields events)
    list(finalize_expense(ctx, "Final Report"))

    # Verify the database contains the Partially Approved expense
    db_items = load_database()
    assert len(db_items) == 1
    assert db_items[0]["merchant"] == "Hilton Hotels"
    assert db_items[0]["status"] == "Partially Approved"

    # Verify execute_query FILTER logic retrieves it
    query_res = execute_query({"action": "FILTER", "category": "Hotel"})
    assert len(query_res["data"]) == 1
    assert query_res["data"][0]["merchant"] == "Hilton Hotels"

    # Verify execute_query COMPARE_DEPTS logic processes Partially Approved status correctly
    compare_res = execute_query({"action": "COMPARE_DEPTS"})
    eng_dept = next(d for d in compare_res["data"] if d["department"] == "Engineering")
    # For Partially Approved, reimbursable and rejected are calculated from the saved values
    assert eng_dept["reimbursable"] == 150.0
    assert eng_dept["rejected"] == 130.0


def test_db_reentrant_lock_safety():
    """Verify the database lock does not deadlock during recursive/reentrant calls."""
    expense = {
        "id": "exp-test-lock-1",
        "merchant": "Subway",
        "amount": 10.0,
        "currency": "USD",
    }

    # This should complete without deadlock since db_lock is reentrant (RLock)
    add_expense_to_db(expense)
    db = load_database()
    assert len(db) == 1
    assert db[0]["id"] == "exp-test-lock-1"


def test_concurrent_lock_persistence():
    """Verify that multiple concurrent threads appending to database do not overwrite/lose updates."""
    thread_count = 20
    threads = []

    def worker(idx):
        expense = {
            "id": f"exp-concurrent-{idx}",
            "merchant": f"Merchant-{idx}",
            "amount": 10.0 + idx,
            "currency": "USD",
        }
        add_expense_to_db(expense)

    for i in range(thread_count):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    db = load_database()
    # Verify that all concurrent writes survived (no lost-updates)
    assert len(db) == thread_count
    for i in range(thread_count):
        assert any(item.get("id") == f"exp-concurrent-{i}" for item in db)
