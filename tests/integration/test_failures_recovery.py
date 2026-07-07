# Copyright 2026 Google LLC
# Failure Recovery validation test script

import asyncio
import os
import sys
from unittest.mock import patch

import pytest

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

# Ensure app is in path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Use mock LLM
os.environ["MOCK_LLM"] = "True"
os.environ["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "false"

from app.agent import receipt_extractor, root_agent


@pytest.mark.asyncio
async def test_mcp_offline_recovery():
    print("\n--- Testing MCP Offline Recovery ---")

    # Temporarily corrupt the connection params of receipt_extractor
    old_toolset = receipt_extractor.tools[0]
    receipt_extractor.tools = [
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="non_existent_command_to_fail", args=[]
                )
            )
        )
    ]

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        user_id="test_user", app_name="fail_test"
    )
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="fail_test"
    )

    prompt = "Please audit this expense: Lunch with client at Pizza Hut on 2026-06-25. Total amount: $35.50 USD. Merchant: Pizza Hut."
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    out = ""
    errors = []
    try:
        async for event in runner.run_async(
            new_message=message, user_id="test_user", session_id=session.id
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        out += part.text + "\n"
    except Exception as e:
        errors.append(str(e))

    await runner.close()

    # Restore old toolset
    receipt_extractor.tools = [old_toolset]

    print("  Errors reported:", errors)
    print("  Output snippet:", out.strip()[:100] + "...")
    # It should complete successfully without crashing, using the agent's fallback reasoning
    assert len(errors) == 0, f"Expected no crash, but got errors: {errors}"
    assert "Pizza Hut" in out, "Expected successful extraction using fallback reasoning"
    print("  MCP Offline Recovery Passed.")


@pytest.mark.asyncio
async def test_gemini_timeout_recovery():
    print("\n--- Testing Gemini Timeout Recovery ---")

    # Mock MockGemini's generate_content_async to raise asyncio.TimeoutError
    async def mock_timeout(*args, **kwargs):
        raise TimeoutError("Gemini connection timed out (mocked).")
        # Yield to satisfy generator protocol
        yield None

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        user_id="test_user", app_name="fail_test"
    )
    runner = Runner(
        agent=receipt_extractor, session_service=session_service, app_name="fail_test"
    )

    prompt = "Please audit this expense: Lunch with client at Pizza Hut on 2026-06-25. Total amount: $35.50 USD. Merchant: Pizza Hut."
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    out = ""
    errors = []

    # Patch the MockGemini's generate_content_async on the root_agent's model
    # Wait, the root_agent's model is at root_agent.model or model
    from app.agent import MockGemini

    try:
        with patch.object(MockGemini, "generate_content_async", mock_timeout):
            async for event in runner.run_async(
                new_message=message, user_id="test_user", session_id=session.id
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            out += part.text + "\n"
    except Exception as e:
        errors.append(str(e))
    finally:
        try:
            await runner.close()
        except Exception as e:
            errors.append(str(e))
        if hasattr(runner, "_root_task") and runner._root_task is not None:
            try:
                exc = runner._root_task.exception()
                if exc:
                    errors.append(str(exc))
            except Exception:
                pass

    print("  Errors reported:", errors)
    # Since timeout is simulated on all retries, it should raise a TimeoutError or McpError/exception
    assert len(errors) > 0, "Expected timeout exception to be raised"
    assert "TimeoutError" in str(errors[0]) or "timed out" in str(errors[0])
    print("  Gemini Timeout Recovery Passed.")


@pytest.mark.asyncio
async def test_malformed_ocr_recovery():
    print("\n--- Testing Malformed OCR Input Recovery ---")

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        user_id="test_user", app_name="fail_test"
    )
    runner = Runner(
        agent=root_agent, session_service=session_service, app_name="fail_test"
    )

    # Empty/malformed receipt text
    prompt = "Please audit this receipt:    "
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    out = ""
    errors = []
    try:
        async for event in runner.run_async(
            new_message=message, user_id="test_user", session_id=session.id
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        out += part.text + "\n"
    except Exception as e:
        errors.append(str(e))

    await runner.close()
    print("  Errors reported:", errors)
    print("  Output snippet:", out.strip()[:100] + "...")
    assert len(errors) == 0, (
        f"Expected no crash on empty input, but got errors: {errors}"
    )
    print("  Malformed OCR Input Recovery Passed.")


async def main():
    print("\n=======================================================")
    print("RUNNING FAILURE RECOVERY VALIDATION TESTS")
    print("=======================================================\n")
    await test_mcp_offline_recovery()
    await test_gemini_timeout_recovery()
    await test_malformed_ocr_recovery()
    print("\nFailure Recovery Validation completed.")


if __name__ == "__main__":
    asyncio.run(main())
