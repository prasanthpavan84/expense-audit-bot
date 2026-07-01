import asyncio
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import root_agent

async def mock_generate_content_async(self, llm_request, stream=False):
    from google.adk.models.llm_response import LlmResponse
    # Mocking receipt_extractor to return multiple expenses
    text = '{"expenses": [' \
           '{"merchant": "Subway", "date": "2026-06-25", "amount": 15.50, "currency": "USD", "category": "Meals", "items": ["Sub", "Drink"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"},' \
           '{"merchant": "Uber", "date": "2026-06-25", "amount": 25.00, "currency": "USD", "category": "Taxi", "items": ["Ride to hotel"], "items_list": [], "ocr_confidence_score": 1.0, "readability_issues": [], "manipulated_receipt": false, "employee_id": "EMP102", "department": "Engineering"}' \
           ']}'
           
    # Intent classifier mock
    contents_str = str(llm_request.contents)
    if "intent_classifier" in contents_str or "Classify the user intent" in contents_str:
        text = '{"intent": "AUDIT"}'
    elif "policy_verifier" in contents_str:
        text = '{"compliant": true, "violations": [], "audit_notes": "Checked limits."}'
        
    response = LlmResponse(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)])
    )
    yield response

class TestMultiExpenseIntegration:
    async def run_multi_audit(self):
        # Set database path to a separate temporary integration test file
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_db_path = os.path.join(project_dir, "tests", "integration", "temp_database.json")
        os.environ["DATABASE_PATH"] = temp_db_path
        try:
            import json
            with open(temp_db_path, "w") as f:
                json.dump([], f)
        except Exception:
            pass

        old_mock = os.environ.get("MOCK_LLM")
        os.environ["MOCK_LLM"] = "False"
        
        session_service = InMemorySessionService()
        session = await session_service.create_session(user_id="test_user", app_name="test")
        runner = Runner(agent=root_agent, session_service=session_service, app_name="test")
        
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text="Please audit these expenses:\n1. Meals: Subway USD $15.50 on 2026-06-25\n2. Taxi: Uber USD $25.00 on 2026-06-25")]
        )
        
        full_text = ""
        # Run with patched Gemini
        with patch(
            "google.adk.models.google_llm.Gemini.generate_content_async",
            mock_generate_content_async
        ):
            async for event in runner.run_async(
                new_message=message,
                user_id="test_user",
                session_id=session.id
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            full_text += part.text + "\n"
                             
        await runner.close()
        
        # Clean up
        if old_mock is not None:
            os.environ["MOCK_LLM"] = old_mock
        elif "MOCK_LLM" in os.environ:
            del os.environ["MOCK_LLM"]
            
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass
        if "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]
        return full_text

def test_multi_expense_workflow():
    test_case = TestMultiExpenseIntegration()
    output = asyncio.run(test_case.run_multi_audit())
    
    # Assertions
    assert "Executive Summary" in output
    assert "Subway" in output
    assert "Uber" in output
    assert "40.50" in output # Total Claimed ($15.50 + $25.00)
    assert "Approved" in output or "Partially Approved" in output
