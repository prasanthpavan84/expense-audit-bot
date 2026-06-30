# Real-time constraint test for expense audit scenarios
# Handles Windows encoding + uses mocked Gemini model to run completely offline without hitting rate limits
import os
import sys
import time
from unittest.mock import patch

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent

# Mock implementation of Gemini's generate_content_async
async def mock_generate_content_async(self, llm_request, stream=False):
    import json
    import re
    contents_str = str(llm_request.contents)

    # Extract system instruction
    si_str = ""
    config = getattr(llm_request, "config", None)
    if config:
        si = getattr(config, "system_instruction", None)
        if si:
            if isinstance(si, str):
                si_str = si
            elif hasattr(si, "parts") and si.parts:
                si_str = "".join(p.text for p in si.parts if p.text)
            else:
                si_str = str(si)

    # Classify intent
    if "intent_classifier" in si_str or "intent_classifier" in contents_str or "Classify the user intent" in contents_str:
        text_lower = contents_str.lower()
        if "policy" in text_lower or "limit" in text_lower or "what is" in text_lower or "rules" in text_lower:
            intent = "POLICY"
        elif "calculate" in text_lower or "reimbursable" in text_lower or "total" in text_lower or ("hotel" in text_lower and "meals" in text_lower and "flight" in text_lower):
            intent = "CALCULATE"
        elif "extract" in text_lower or "receipt" in text_lower:
            intent = "EXTRACT"
        elif "compare" in text_lower or "summarize" in text_lower or "query" in text_lower or "departments" in text_lower:
            intent = "QUERY"
        else:
            intent = "AUDIT"
        text = f'{{"intent": "{intent}"}}'

    # 1. receipt_extractor
    elif (
        "receipt_extractor" in si_str
        or "Receipt Extractor" in si_str
        or "Receipt Extractor" in contents_str
        or "extractor" in contents_str
        or "Analyze the user's input" in contents_str
    ):
        if "Pizza Hut" in contents_str:
            if "75.00" in contents_str or "75" in contents_str:
                text = '{"expenses": [{"merchant": "Pizza Hut", "date": "2026-06-25", "amount": 75.00, "currency": "USD", "category": "Meals", "items": ["2 Pizzas", "1 Salad", "2 Sodas"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
            elif "2026-06-27" in contents_str:
                text = '{"expenses": [{"merchant": "Pizza Hut", "date": "2026-06-27", "amount": 35.50, "currency": "USD", "category": "Meals", "items": ["2 Pizzas"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
            else:
                text = '{"expenses": [{"merchant": "Pizza Hut", "date": "2026-06-25", "amount": 35.50, "currency": "USD", "category": "Meals", "items": ["2 Pizzas", "1 Salad", "2 Sodas"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
        elif "Gold Club Bar" in contents_str:
            if "120.00" in contents_str or "120" in contents_str:
                text = '{"expenses": [{"merchant": "Gold Club Bar", "date": "2026-06-27", "amount": 120.00, "currency": "USD", "category": "Restricted", "items": ["Beer", "cocktails"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
            else:
                text = '{"expenses": [{"merchant": "Gold Club Bar", "date": "2026-06-27", "amount": 90.00, "currency": "USD", "category": "Restricted", "items": ["Beer", "cocktails"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
        elif "Hilton" in contents_str or "EUR" in contents_str:
            text = '{"expenses": [{"merchant": "Hilton", "date": "2026-06-26", "amount": 150.00, "currency": "EUR", "category": "Hotel", "items": ["Room stay"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
        elif "Taxi" in contents_str and ("-150" in contents_str or "- 150" in contents_str):
            text = '{"expenses": [{"merchant": "Taxi", "date": "2026-06-25", "amount": -150.0, "currency": "INR", "category": "Taxi", "items": ["Ride"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
        elif "Taxi ride" in contents_str or "unknown" in contents_str or "Unknown" in contents_str:
            text = '{"expenses": [{"merchant": "Taxi ride", "date": "Unknown", "amount": 15.00, "currency": "USD", "category": "Meals", "items": ["Ride"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'
        else:
            text = '{"expenses": [{"merchant": "Unknown", "date": "Unknown", "amount": 0.0, "currency": "USD", "category": "Other", "items": [], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}]}'

    # 2. policy_verifier
    elif (
        "policy_verifier" in si_str
        or "Policy Verifier" in si_str
        or "Policy Verifier" in contents_str
        or "verifier" in contents_str
        or "Compare the provided expense details" in contents_str
    ):
        text = '{"compliant": true, "violations": [], "audit_notes": "Policy limits checked."}'

    # 3. audit_orchestrator / fallback
    else:
        text = "APPROVED"

    response = LlmResponse(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)])
    )
    yield response


SCENARIOS = {
    "A_AUTO_APPROVED": {
        "input": (
            "Please audit this expense: Lunch with a client at Pizza Hut on "
            "2026-06-25. Total amount: $35.50 USD. Merchant: Pizza Hut. "
            "Items: 2 Pizzas, 1 Salad, 2 Sodas."
        ),
        "expect_contains": ["approved"],
        "expect_not": ["denied", "exception"],
        "max_seconds": 30,
    },
    "C_AUTO_DENIED": {
        "input": (
            "Please audit this expense: Team celebratory drinks at Gold Club Bar "
            "on 2026-06-27. Total amount: $90.00 USD. Items: Beer, cocktails."
        ),
        "expect_contains": ["denied"],
        "expect_not": [],
        "max_seconds": 30,
    },
    "D_CONFERENCE_EXCEPTION": {
        "input": (
            "Please audit this expense: Lunch with a client at Pizza Hut on "
            "2026-06-25. Total amount: $75.00 USD. Attended the annual tech conference."
        ),
        "expect_contains": ["Approved with Exception", "Conference Justification"],
        "expect_not": ["denied"],
        "max_seconds": 30,
    },
    "E_EXECUTIVE_APPROVAL": {
        "input": (
            "Please audit this expense: Team celebrating dinner at Gold Club Bar "
            "on 2026-06-27. Total amount: $120.00 USD. CEO approved."
        ),
        "expect_contains": ["Approved with Exception", "Executive Approval Justification"],
        "expect_not": ["denied"],
        "max_seconds": 30,
    },
    "F_HUMAN_REVIEW_CURRENCY": {
        "input": (
            "Please audit this expense: Hotel stay at Hilton on 2026-06-26. "
            "Total amount: 150.00 EUR."
        ),
        "expect_contains": ["Needs Human Review", "Unsupported currency"],
        "expect_not": [],
        "max_seconds": 30,
    },
    "G_HUMAN_REVIEW_MISSING_INFO": {
        "input": (
            "Please audit this expense: Taxi ride. Total amount: $15.00 USD. Date is unknown."
        ),
        "expect_contains": ["Needs Human Review", "Missing required information"],
        "expect_not": [],
        "max_seconds": 30,
    },
    "H_VALIDATION_NEGATIVE": {
        "input": (
            "Please audit this expense:\nTaxi ₹-150\n"
        ),
        "expect_contains": ["Validation Failure", "Rejected", "Amounts must be positive"],
        "expect_not": ["Approved"],
        "max_seconds": 30,
    },
    "I_NATURAL_QUERY_COMPARISON": {
        "input": (
            "Compare departments and spending trends"
        ),
        "expect_contains": ["Department Spending Comparison", "Approved"],
        "expect_not": ["denied"],
        "max_seconds": 30,
    },
    "J_FRAUD_WEEKEND_ANOMALY": {
        "input": (
            "Please audit this expense: Lunch with client at Pizza Hut on 2026-06-27. Total amount: $35.50 USD. Merchant: Pizza Hut. Items: 2 Pizzas."
        ),
        "expect_contains": ["Fraud Analysis", "weekend", "Approved"],
        "expect_not": ["denied"],
        "max_seconds": 30,
    },
}

# No cooldown needed with mocked model
INTER_SCENARIO_DELAY = 0


def run_scenario(name, spec):
    print(f"\n{'=' * 70}")
    print(f"  SCENARIO {name}")
    print(f"{'=' * 70}")
    print(f"  Input: {spec['input'][:80]}...")
    print(f"  Time limit: {spec['max_seconds']}s")
    print()

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=spec["input"])],
    )

    start = time.time()
    events = []
    errors = []
    full_text = ""

    try:
        for event in runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            elapsed = time.time() - start
            events.append(event)

            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        full_text += part.text + "\n"

            if hasattr(event, "error") and event.error:
                errors.append(str(event.error))
                print(f"  [ERROR at {elapsed:.1f}s] {event.error}")

            if elapsed > spec["max_seconds"]:
                errors.append(f"TIMEOUT after {elapsed:.1f}s")
                break

    except Exception as e:
        elapsed = time.time() - start
        errors.append(f"Exception: {e}")
        print(f"  [EXCEPTION at {elapsed:.1f}s] {e}")

    elapsed = time.time() - start

    text_lower = full_text.lower()
    passed_checks = []
    failed_checks = []

    for keyword in spec["expect_contains"]:
        if keyword.lower() in text_lower:
            passed_checks.append(f"[PASS] Contains '{keyword}'")
        else:
            failed_checks.append(f"[FAIL] Missing expected '{keyword}'")

    for keyword in spec["expect_not"]:
        if keyword.lower() in text_lower:
            failed_checks.append(f"[FAIL] Unexpectedly contains '{keyword}'")
        else:
            passed_checks.append(f"[PASS] Correctly does not contain '{keyword}'")

    if not errors:
        passed_checks.append("[PASS] No errors")
    else:
        failed_checks.append(f"[FAIL] {len(errors)} error(s): {errors}")

    if elapsed <= spec["max_seconds"]:
        passed_checks.append(
            f"[PASS] Completed in {elapsed:.1f}s (limit: {spec['max_seconds']}s)"
        )
    else:
        failed_checks.append(
            f"[FAIL] Exceeded time limit: {elapsed:.1f}s > {spec['max_seconds']}s"
        )

    status = "PASS" if not failed_checks else "FAIL"

    print(f"  Events received: {len(events)}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print("  Response (first 500 chars):")
    print(f"  {full_text[:500]}")
    print()
    for c in passed_checks:
        print(f"  {c}")
    for c in failed_checks:
        print(f"  {c}")
    print(f"\n  >>> RESULT: {status}")

    return {
        "name": name,
        "status": status,
        "elapsed": elapsed,
        "events": len(events),
        "errors": errors,
        "passed": passed_checks,
        "failed": failed_checks,
    }


def main():
    # Reset database.json to prevent duplicate failures from previous runs
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_dir, "app", "database.json")
    try:
        import json
        with open(db_path, "w") as f:
            json.dump([], f)
    except Exception:
        pass

    print("\n" + "=" * 70)
    print("  EXPENSE AUDIT BOT - REAL-TIME CONSTRAINT TESTS (MOCKED)")
    print("=" * 70)

    results = []
    scenario_list = list(SCENARIOS.items())

    # Patch the Gemini generate_content_async call globally during run
    with patch(
        "google.adk.models.google_llm.Gemini.generate_content_async",
        mock_generate_content_async,
    ):
        for i, (name, spec) in enumerate(scenario_list):
            result = run_scenario(name, spec)
            results.append(result)

            if i < len(scenario_list) - 1 and INTER_SCENARIO_DELAY > 0:
                print(
                    f"\n  >> Waiting {INTER_SCENARIO_DELAY}s for rate-limit cooldown..."
                )
                time.sleep(INTER_SCENARIO_DELAY)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    total_pass = sum(1 for r in results if r["status"] == "PASS")
    total_fail = sum(1 for r in results if r["status"] == "FAIL")

    for r in results:
        icon = "[PASS]" if r["status"] == "PASS" else "[FAIL]"
        print(
            f"  {icon} {r['name']}: {r['status']} ({r['elapsed']:.1f}s, {r['events']} events)"
        )

    print(f"\n  Total: {total_pass} passed, {total_fail} failed out of {len(results)}")
    print("=" * 70)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
