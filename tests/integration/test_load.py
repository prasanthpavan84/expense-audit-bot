# Copyright 2026 Google LLC
# Load validation test script

import asyncio
import json
import os
import sys
import time

import numpy as np
import psutil
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Ensure app is in path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Use mock LLM to avoid quota exhaustion during load test
os.environ["MOCK_LLM"] = "True"
os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "false"

# Use temporary database path
PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
TEMP_DB_PATH = os.path.join(PROJECT_DIR, "tests", "integration", "temp_load_db.json")
os.environ["DATABASE_PATH"] = TEMP_DB_PATH

from app.agent import root_agent


async def send_single_load_request(request_id: int) -> float:
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        user_id=f"load_user_{request_id}", app_name="load_test"
    )
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="load_test"
    )

    prompt = f"Please audit this expense: Taxi ride. Merchant: Taxi ride. Date: 2026-06-25. Total amount: ${15.00 + (request_id % 10):.2f} USD."
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    start_time = time.time()
    try:
        async for _event in runner.run_async(
            new_message=message,
            user_id=f"load_user_{request_id}",
            session_id=session.id,
        ):
            pass
        success = True
    except Exception:
        success = False

    elapsed = time.time() - start_time
    await runner.close()

    if not success:
        return -1.0
    return elapsed


async def run_load_test(duration_seconds: int = 20, rate_per_second: int = 3):
    print(
        f"Starting Load Test: sustaining {rate_per_second} req/sec for {duration_seconds} seconds..."
    )

    # Initialize clean database
    with open(TEMP_DB_PATH, "w") as f:
        json.dump([], f)

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    cpu_before = process.cpu_percent(interval=None)

    latencies: list[float] = []
    failures = 0
    total_sent = 0

    start_time = time.time()
    loop_start = time.time()

    while time.time() - start_time < duration_seconds:
        # Send a batch of requests
        tasks = []
        for _ in range(rate_per_second):
            tasks.append(send_single_load_request(total_sent))
            total_sent += 1

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in batch_results:
            if isinstance(r, BaseException) or r < 0:
                failures += 1
            else:
                latencies.append(r)

        # Sleep to maintain rate
        elapsed = time.time() - loop_start
        sleep_time = max(0.0, 1.0 - elapsed)
        await asyncio.sleep(sleep_time)
        loop_start = time.time()

    mem_after = process.memory_info().rss / (1024 * 1024)
    cpu_after = process.cpu_percent(interval=None)

    total_completed = len(latencies)

    # Calculate latency percentiles
    if latencies:
        avg_lat = np.mean(latencies)
        p95_lat = np.percentile(latencies, 95)
        p99_lat = np.percentile(latencies, 99)
    else:
        avg_lat, p95_lat, p99_lat = 0, 0, 0

    mem_delta = mem_after - mem_before
    cpu_used = cpu_after - cpu_before

    print("\nLoad Test Summary:")
    print(f"  Total Sent: {total_sent}")
    print(f"  Successful: {total_completed}")
    print(f"  Failures: {failures} ({failures / total_sent:.1%})")
    print(f"  Avg Latency: {avg_lat:.2f}s")
    print(f"  P95 Latency: {p95_lat:.2f}s")
    print(f"  P99 Latency: {p99_lat:.2f}s")
    print(f"  Memory Delta: {mem_delta:.2f} MB")
    print(f"  CPU Delta: {cpu_used:.2f}%")

    # Clean up temp db
    if os.path.exists(TEMP_DB_PATH):
        try:
            os.remove(TEMP_DB_PATH)
        except Exception:
            pass

    # Save Report
    report_path = os.path.join(PROJECT_DIR, "Evaluation_Report", "load_test_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Sustained Load Testing Report\n\n")
        f.write("## Execution Metrics\n\n")
        f.write(f"- **Total Requests Sent**: {total_sent}\n")
        f.write(f"- **Successful Requests**: {total_completed}\n")
        f.write(f"- **Failed Requests**: {failures} ({failures / total_sent:.2%})\n")
        f.write(f"- **Avg Latency**: {avg_lat:.3f} seconds\n")
        f.write(f"- **P95 Latency**: {p95_lat:.3f} seconds\n")
        f.write(f"- **P99 Latency**: {p99_lat:.3f} seconds\n")
        f.write(f"- **Memory Usage RSS Delta**: {mem_delta:.2f} MB\n")
        f.write(f"- **CPU Usage Delta**: {cpu_used:.2f}%\n")

    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(run_load_test())
