import uvicorn
from fastapi import FastAPI

from .api.routes import router as api_router
from .middleware.conversation_middleware import ConversationMiddleware

app = FastAPI(title="Expense Audit Bot", version="0.1.0")

# Add middleware for session handling
app.add_middleware(ConversationMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v2")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)  # nosec
