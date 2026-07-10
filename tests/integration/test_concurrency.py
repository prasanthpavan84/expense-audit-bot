# Copyright 2026 Google LLC
# Concurrency validation test script

import asyncio
import json
import os
import sys
import time

import psutil
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Use mock LLM to avoid quota exhaustion during concurrent pressure test
os.environ["MOCK_LLM"] = "True"
os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "false"

# Use temporary database path for isolation
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DB_PATH = os.path.join(PROJECT_DIR, "tests", "integration", "temp_concurrency_db.json")
os.environ["DATABASE_PATH"] = TEMP_DB_PATH

from app.agent import root_agent


async def execute_single_request(request_id: int) -> dict:
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id=f"user_{request_id}", app_name="concurrency_test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="concurrency_test")

    prompt = f"Please audit this expense: Lunch with client at Pizza Hut on 2026-06-25. Total amount: ${10.00 + request_id:.2f} USD. Merchant: Pizza Hut. Items: Pizza."
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    start_time = time.time()
    full_text = ""
    errors = []

    try:
        async for event in runner.run_async(new_message=message, user_id=f"user_{request_id}", session_id=session.id):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        full_text += part.text + "\n"
    except Exception as e:
        errors.append(str(e))

    elapsed = time.time() - start_time
    await runner.close()

    return {
        "request_id": request_id,
        "elapsed": elapsed,
        "errors": errors,
        "success": len(errors) == 0 and "Approved" in full_text,
    }


async def run_concurrency_batch(concurrency_level: int) -> dict:
    # Initialize clean database
    with open(TEMP_DB_PATH, "w") as f:
        json.dump([], f)

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    cpu_before = process.cpu_percent(interval=None)

    start_time = time.time()
    tasks = [execute_single_request(i) for i in range(concurrency_level)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.time() - start_time

    mem_after = process.memory_info().rss / (1024 * 1024)
    cpu_after = process.cpu_percent(interval=None)

    success_count = 0
    failures = []

    for r in results:
        if isinstance(r, Exception):
            failures.append(str(r))
        elif not r["success"]:
            failures.append(f"Req {r['request_id']} failed: {r['errors']}")
        else:
            success_count += 1

    # Verify database integrity
    try:
        with open(TEMP_DB_PATH) as f:
            db_data = json.load(f)
        db_count = len(db_data)
    except Exception as e:
        db_count = -1
        failures.append(f"Failed to read db: {e}")

    return {
        "level": concurrency_level,
        "elapsed": elapsed,
        "tps": concurrency_level / elapsed if elapsed > 0 else 0,
        "success_rate": success_count / concurrency_level,
        "db_count": db_count,
        "mem_delta": mem_after - mem_before,
        "cpu_used": cpu_after - cpu_before,
        "failures": failures,
    }


async def main():
    print("\n=======================================================")
    print("RUNNING CONCURRENT REQUEST VALIDATION TESTS")
    print("=======================================================\n")

    levels = [10, 25, 50]
    batch_results = []

    for lvl in levels:
        print(f"Testing {lvl} concurrent requests...")
        res = await run_concurrency_batch(lvl)
        print(
            f"  Completed in {res['elapsed']:.2f}s | TPS: {res['tps']:.2f} | Success Rate: {res['success_rate']:.1%} | DB Entries: {res['db_count']}"
        )
        if res["failures"]:
            print(f"  Failures detected: {res['failures'][:3]}")
        batch_results.append(res)
        await asyncio.sleep(1.0)

    # Clean up temp db
    if os.path.exists(TEMP_DB_PATH):
        try:
            os.remove(TEMP_DB_PATH)
        except Exception:
            pass

    # Save Report
    report_path = os.path.join(PROJECT_DIR, "Evaluation_Report", "concurrency_test_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Concurrent Request Testing Report\n\n")
        f.write("## Summary\n\n")
        f.write(
            "| Concurrent Requests | Duration (s) | TPS | Success Rate | DB Count | Memory Delta (MB) | Failures |\n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for r in batch_results:
            f.write(
                f"| {r['level']} | {r['elapsed']:.2f} | {r['tps']:.2f} | {r['success_rate']:.1%} | {r['db_count']} | {r['mem_delta']:.2f} | {len(r['failures'])} |\n"
            )

    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
