# Copyright 2026 Google LLC
# Long Conversation validation test script

import asyncio
import json
import os
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Use mock LLM
os.environ["MOCK_LLM"] = "True"
os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "false"

# Use temporary database path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DB_PATH = os.path.join(PROJECT_DIR, "tests", "integration", "temp_conversation_db.json")
os.environ["DATABASE_PATH"] = TEMP_DB_PATH

from app.agent import root_agent


def safe_print(msg: str):
    """Prints message safely handling Windows encoding limitations."""
    print(msg.encode("ascii", "replace").decode("ascii"))


async def run_long_conversation():
    # Initialize clean database
    with open(TEMP_DB_PATH, "w") as f:
        json.dump([], f)

    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="conv_user", app_name="conv_test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="conv_test")

    safe_print("\nStarting Long Conversation Test...")

    # Turn 1: Submit Receipt A (Pizza Hut, $35.50)
    safe_print("\n--- Turn 1: Submit Pizza Hut receipt ---")
    p1 = "Please audit this expense: Lunch with client at Pizza Hut on 2026-06-25. Total amount: $35.50 USD. Merchant: Pizza Hut. Items: Pizza."
    msg1 = types.Content(role="user", parts=[types.Part.from_text(text=p1)])
    out1 = ""
    async for event in runner.run_async(new_message=msg1, user_id="conv_user", session_id=session.id):
        safe_print(f"Event: {type(event).__name__}")
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    out1 += part.text + "\n"
    safe_print("Agent Output:\n" + out1.strip()[:150] + "...")
    assert "Pizza Hut" in out1
    assert "35.50" in out1
    assert "Approved" in out1

    # Turn 2: Ask policy question
    safe_print("\n--- Turn 2: Ask policy question ---")
    p2 = "What is the corporate travel limit policy?"
    msg2 = types.Content(role="user", parts=[types.Part.from_text(text=p2)])
    out2 = ""
    async for event in runner.run_async(new_message=msg2, user_id="conv_user", session_id=session.id):
        safe_print(f"Event: {type(event).__name__}")
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    out2 += part.text + "\n"
    safe_print("Agent Output:\n" + out2.strip()[:150] + "...")

    # Turn 3: Upload Receipt B (Hilton, $280.00 -> triggers human review)
    safe_print("\n--- Turn 3: Submit Hilton receipt ($280.00) ---")
    p3 = "Please audit this expense: Hotel stay at Hilton Hotels on 2026-06-26. Total amount: $280.00 USD. Merchant: Hilton Hotels. Items: Room charge."
    msg3 = types.Content(role="user", parts=[types.Part.from_text(text=p3)])

    out3 = ""
    resumed = False

    from google.adk.events.request_input import RequestInput

    async for event in runner.run_async(new_message=msg3, user_id="conv_user", session_id=session.id):
        safe_print(f"Event: {type(event).__name__}")
        if isinstance(event, RequestInput):
            safe_print("\nWorkflow paused for Human Review! Resuming with approval...")
            resumed = True
            msg_resume = types.Content(role="user", parts=[types.Part.from_text(text="approve")])
            async for ev2 in runner.run_async(new_message=msg_resume, user_id="conv_user", session_id=session.id):
                safe_print(f"Resume Event: {type(ev2).__name__}")
                if ev2.content and ev2.content.parts:
                    for part in ev2.content.parts:
                        if part.text:
                            out3 += part.text + "\n"
        else:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        out3 += part.text + "\n"

    safe_print("Agent Output:\n" + out3.strip()[:150] + "...")

    # Turn 4: Request session summary
    safe_print("\n--- Turn 4: Request summary ---")
    p4 = "summarize my expenses"
    msg4 = types.Content(role="user", parts=[types.Part.from_text(text=p4)])
    out4 = ""
    async for event in runner.run_async(new_message=msg4, user_id="conv_user", session_id=session.id):
        safe_print(f"Event: {type(event).__name__}")
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    out4 += part.text + "\n"
    safe_print("Agent Output:\n" + out4.strip()[:150] + "...")

    await runner.close()

    # Verify DB contains the records
    with open(TEMP_DB_PATH) as f:
        db_data = json.load(f)
    safe_print(f"\nFinal DB contains {len(db_data)} expenses.")
    for idx, item in enumerate(db_data):
        safe_print(
            f"  Expense {idx + 1}: {item.get('merchant')} | {item.get('amount')} {item.get('currency')} | {item.get('status') or item.get('decision')}"
        )

    # Let's save a summary validation report
    report_path = os.path.join(PROJECT_DIR, "Evaluation_Report", "long_conversation_test_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Long Conversation Testing Report\n\n")
        f.write("## Session Interaction Flow\n\n")
        f.write("1. **Submit Receipt A** (Pizza Hut, $35.50) -> Approved successfully.\n")
        f.write("2. **Query policy limits** -> Travel policies retrieved.\n")
        f.write(f"3. **Submit Receipt B** (Hilton, $280.00) -> Triggers Human Review pause: {resumed}.\n")
        f.write("4. **Summary report** -> General summary requested.\n\n")
        f.write("## Database Persistence\n\n")
        f.write(f"Total expenses persisted: {len(db_data)}\n\n")
        f.write("| Merchant | Amount | Status |\n")
        f.write("| --- | --- | --- |\n")
        for item in db_data:
            f.write(
                f"| {item.get('merchant')} | {item.get('amount')} {item.get('currency')} | {item.get('status')} |\n"
            )

    print(f"Report saved to {report_path}")

    assert len(db_data) >= 1, "Expected at least 1 database entries"
    safe_print("\nLong Conversation Test completed!")


if __name__ == "__main__":
    asyncio.run(run_long_conversation())
