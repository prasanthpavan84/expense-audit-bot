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

import contextlib
import os
from collections.abc import AsyncIterator

import google.auth
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.cloud import logging as google_cloud_logging

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.reasoning_engine_adapter import (
    attach_reasoning_engine_routes,
)
from app.app_utils.telemetry import (
    setup_agent_engine_telemetry,
    setup_telemetry,
)
from app.app_utils.typing import Feedback

load_dotenv()
setup_telemetry()
# Must run before get_fast_api_app to set the tracer provider resource.
setup_agent_engine_telemetry()
import logging
logger = logging.getLogger(__name__)

try:
    _, project_id = google.auth.default()
    logging_client = google_cloud_logging.Client()
    cloud_logger = logging_client.logger(__name__)
    
    class CloudLoggerAdapter:
        def __init__(self, c_logger):
            self.c_logger = c_logger
        def log_struct(self, data: dict, severity: str = "INFO"):
            try:
                self.c_logger.log_struct(data, severity=severity)
            except Exception:
                logger.info(f"CLOUD_LOG ({severity}): {data}")
                
    logger = CloudLoggerAdapter(cloud_logger)
except Exception:
    project_id = None
    class FallbackLogger:
        def log_struct(self, data: dict, severity: str = "INFO"):
            logger.info(f"LOCAL_LOG ({severity}): {data}")
    logger = FallbackLogger()

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runner for the A2A path, sharing the same session/artifact services as the
    # adk_api and reasoning_engine paths (see services.py). Imported here so the
    # agent is built after env/telemetry setup.
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    # Shared by the A2A path and the reasoning_engine adapter routes.
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=False,
    lifespan=lifespan,
)
app.title = "expense-audit-bot"
app.description = "API for interacting with the Agent expense-audit-bot"

# Integrate Correlation ID tracking middleware
from app.middleware.trace_middleware import CorrelationIdMiddleware
app.add_middleware(CorrelationIdMiddleware)

# Integrate versioned API routes
from app.api.v1.v1_routes import router as api_v1_router
app.include_router(api_v1_router, prefix="/api/v1")

# WebSocket Endpoint for streaming real-time console logs
from app.api.v1.websocket_manager import manager as ws_manager, subscribe_event_bus_to_websockets
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/api/v1/ws/console")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# Hook up event bus subscriptions to broadcast via websockets
subscribe_event_bus_to_websockets()

# Structured Exception Handlers
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.utils.logger import trace_id_var
import datetime

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": str(exc),
            "trace_id": trace_id_var.get(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "trace_id": trace_id_var.get(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": str(exc.errors()),
            "trace_id": trace_id_var.get(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
    )

# Serve the static Single Page Application (SPA) dashboard
from fastapi.staticfiles import StaticFiles
os.makedirs("app/dashboard", exist_ok=True)
app.mount("/dashboard", StaticFiles(directory="app/dashboard", html=True), name="dashboard")

# reasoning engine adapter routes and collect feedback endpoint
from app.app_utils.typing import Feedback
attach_reasoning_engine_routes(app)

@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    try:
        logger.log_struct(feedback.model_dump(), severity="INFO")
    except Exception:
        # Fallback if logger is a standard logging.Logger
        import logging
        logging.getLogger(__name__).info(f"Feedback: {feedback.model_dump()}")
    return {"status": "success"}



# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
