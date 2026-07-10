from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..conversation.memory import SessionMemory


class ConversationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle session tracking and attach session state to the request."""

    async def dispatch(self, request: Request, call_next):
        # Extract session_id from headers or query parameters
        session_id = request.headers.get("x-session-id") or request.query_params.get("session_id") or "default-session"
        # Fetch or initialize session memory
        session = SessionMemory.get_session(session_id)
        request.state.session = session

        response = await call_next(request)
        response.headers["x-session-id"] = session.get("session_id", "default")
        return response
