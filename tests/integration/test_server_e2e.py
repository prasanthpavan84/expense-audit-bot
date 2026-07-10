# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
import requests
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendStreamingMessageRequest,
    SendStreamingMessageResponse,
    TextPart,
)
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"
RUN_SSE_URL = BASE_URL + "/run_sse"
A2A_RPC_URL = BASE_URL + "/a2a/app/"
AGENT_CARD_URL = A2A_RPC_URL + ".well-known/agent-card.json"
FEEDBACK_URL = BASE_URL + "/feedback"

HEADERS = {"Content-Type": "application/json"}


stdout_lines = []
stderr_lines = []


def log_output(pipe: Any, log_func: Any, lines_accumulator: list[str]) -> None:
    """Log the output from the given pipe and accumulate it."""
    for line in iter(pipe.readline, ""):
        lines_accumulator.append(line)
        log_func(line.strip())


def start_server() -> subprocess.Popen[str]:
    """Start the FastAPI server using subprocess and log its output."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.fast_api_app:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    env = os.environ.copy()
    env["INTEGRATION_TEST"] = "TRUE"
    # Phase 2: Disable telemetry in CI/tests to prevent credential dependency
    env["GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"] = "false"

    stdout_lines.clear()
    stderr_lines.clear()

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    # Start threads to log stdout and stderr in real-time
    threading.Thread(target=log_output, args=(process.stdout, logger.info, stdout_lines), daemon=True).start()
    threading.Thread(target=log_output, args=(process.stderr, logger.error, stderr_lines), daemon=True).start()

    return process


def wait_for_server(process: subprocess.Popen[str], timeout: int = 90, interval: float = 0.5) -> bool:
    """Wait for the server to be ready (agent card requires the lifespan to run)."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Phase 3: Check if the process terminated early
        ret_code = process.poll()
        if ret_code is not None:
            logger.error(f"Server process terminated early with exit code {ret_code}")
            return False

        try:
            response = requests.get(AGENT_CARD_URL, timeout=5)
            if response.status_code == 200:
                logger.info("Server is ready")
                return True
        except RequestException:
            pass
        time.sleep(interval)
    logger.error(f"Server did not become ready within {timeout} seconds")
    return False


def get_redacted_env() -> dict[str, str]:
    """Return a copy of the environment variables with sensitive keys redacted."""
    sensitive_substrings = {"key", "secret", "token", "password", "auth", "credential", "private", "api"}
    redacted = {}
    for k, v in os.environ.items():
        k_lower = k.lower()
        if any(s in k_lower for s in sensitive_substrings):
            redacted[k] = "********"
        else:
            redacted[k] = v
    return redacted


@pytest.fixture(scope="session")
def server_fixture(request: Any) -> Iterator[subprocess.Popen[str]]:
    """Pytest fixture to start and stop the server for testing."""
    logger.info("Starting server process")
    server_process = start_server()
    timeout = int(os.getenv("STARTUP_TIMEOUT", "90"))
    if not wait_for_server(server_process, timeout=timeout):
        ret_code = server_process.poll()
        stdout_content = "".join(stdout_lines)
        stderr_content = "".join(stderr_lines)
        cwd = os.getcwd()
        command_str = " ".join(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.fast_api_app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ]
        )

        # Write logs to disk for CI artifact uploads
        try:
            with open("stdout.log", "w", encoding="utf-8") as f:
                f.write(stdout_content)
            with open("stderr.log", "w", encoding="utf-8") as f:
                f.write(stderr_content)
        except Exception as e:
            logger.error(f"Failed to write log files: {e}")

        try:
            server_process.terminate()
            server_process.wait(timeout=5)
        except Exception:
            pass

        env_vars_str = json.dumps(get_redacted_env(), indent=2)
        diagnostic_msg = (
            f"\nServer failed to start\n"
            f"Exit Code: {ret_code}\n"
            f"Timeout Duration: {timeout} seconds\n"
            f"Startup Command: {command_str}\n"
            f"Working Directory: {cwd}\n"
            f"Environment Variables:\n{env_vars_str}\n"
            f"----------------------------------------\n"
            f"stdout:\n{stdout_content}\n"
            f"----------------------------------------\n"
            f"stderr:\n{stderr_content}\n"
            f"----------------------------------------\n"
        )
        pytest.fail(diagnostic_msg)

    logger.info("Server process started")

    def stop_server() -> None:
        logger.info("Stopping server process")
        server_process.terminate()
        server_process.wait()
        logger.info("Server process stopped")

    request.addfinalizer(stop_server)
    yield server_process


def test_adk_run_sse(server_fixture: subprocess.Popen[str]) -> None:
    """Test the native ADK route (/run_sse) end to end."""
    logger.info("Starting ADK /run_sse test")
    user_id = f"user_{uuid.uuid4()}"
    session_data = {"state": {"preferred_language": "English", "visit_count": 1}}

    session_response = requests.post(
        f"{BASE_URL}/apps/app/users/{user_id}/sessions",
        headers=HEADERS,
        json=session_data,
        timeout=60,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]

    data = {
        "app_name": "app",
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": "Hi!"}]},
        "streaming": True,
    }
    response = requests.post(RUN_SSE_URL, headers=HEADERS, json=data, stream=True, timeout=60)
    assert response.status_code == 200

    events = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                events.append(json.loads(line_str[6:]))

    assert events, "No events received from stream"
    has_text_content = any(
        (content := event.get("content"))
        and content.get("parts")
        and any(part.get("text") for part in content["parts"])
        for event in events
    )
    assert has_text_content, "Expected at least one event with text content"


def test_a2a_chat_stream(server_fixture: subprocess.Popen[str]) -> None:
    """Test the A2A route using the JSON-RPC streaming protocol."""
    logger.info("Starting A2A chat stream test")

    message = Message(
        message_id=f"msg-user-{uuid.uuid4()}",
        role=Role.user,
        parts=[Part(root=TextPart(text="Hi!"))],
    )
    request = SendStreamingMessageRequest(
        id="test-req-001",
        params=MessageSendParams(message=message),
    )
    response = requests.post(
        A2A_RPC_URL,
        headers=HEADERS,
        json=request.model_dump(mode="json", exclude_none=True),
        stream=True,
        timeout=60,
    )
    assert response.status_code == 200

    responses: list[SendStreamingMessageResponse] = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                responses.append(SendStreamingMessageResponse.model_validate(json.loads(line_str[6:])))

    assert responses, "No responses received from stream"

    final_responses = [
        r.root
        for r in responses
        if hasattr(r.root, "result") and hasattr(r.root.result, "final") and r.root.result.final is True
    ]
    assert final_responses, "No final response received"
    assert final_responses[-1].result.status.state == "completed"


def test_agent_card(server_fixture: subprocess.Popen[str]) -> None:
    """Test that the A2A agent card is served at the well-known URI."""
    response = requests.get(AGENT_CARD_URL, timeout=10)
    assert response.status_code == 200, f"A2A endpoint returned {response.status_code}"

    served_agent_card = response.json()
    for field in ("name", "description", "skills", "capabilities", "url", "version"):
        assert field in served_agent_card, f"Missing field in agent card: {field}"


def test_collect_feedback(server_fixture: subprocess.Popen[str]) -> None:
    """Test the feedback collection endpoint (/feedback)."""
    feedback_data = {
        "score": 4,
        "user_id": "test-user-456",
        "session_id": "test-session-456",
        "text": "Great response!",
    }
    response = requests.post(FEEDBACK_URL, json=feedback_data, headers=HEADERS, timeout=10)
    assert response.status_code == 200


def test_reasoning_engine_stream(server_fixture: subprocess.Popen[str]) -> None:
    """The reasoning_engine adapter (/api/stream_reasoning_engine) runs the agent.

    This is the contract Agent Engine forwards :streamQuery calls to.
    """
    response = requests.post(
        f"{BASE_URL}/api/stream_reasoning_engine",
        headers=HEADERS,
        json={
            "class_method": "async_stream_query",
            "input": {"user_id": f"u-{uuid.uuid4()}", "message": "Hi!"},
        },
        stream=True,
        timeout=60,
    )
    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events, "No events from reasoning_engine adapter"
    has_text = any(
        (event.get("content") or {}).get("parts") and any(part.get("text") for part in event["content"]["parts"])
        for event in events
    )
    assert has_text, "No text content in reasoning_engine events"
