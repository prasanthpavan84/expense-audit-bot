import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import trace_id_var

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to set X-Correlation-ID for tracking request lifecycles across logs and endpoints."""
    async def dispatch(self, request: Request, call_next):
        # Resolve correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            
        # Set ContextVar for logging
        token = trace_id_var.set(correlation_id)
        
        try:
            response = await call_next(request)
            # Inject into response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            # Reset ContextVar
            trace_id_var.reset(token)
