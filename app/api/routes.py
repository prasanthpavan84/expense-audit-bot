# app/api/routes.py
"""API routers for the Expense Audit Bot.
Includes the primary `/audit` endpoint.
"""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..pipeline.decision import DecisionEngine
from ..pipeline.explain import ExplainabilityEngine
from ..pipeline.parser import parse_expense
from ..pipeline.validator import validate_expense

router = APIRouter()


@router.post("/audit")
async def audit_expense(request: Request):
    """Audit an expense submission.
    Expects a JSON payload with the required fields for parsing.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {exc!s}")

    try:
        # 1. Parse payload to Expense object
        expense = parse_expense(payload)

        # 2. Validate expense object
        validate_expense(expense)

        # 3. Run decision pipeline (fraud detection and policy evaluation are orchestrated here)
        decision = DecisionEngine().run(expense)

        # 4. Generate human-readable explanation
        session = getattr(request.state, "session", None)
        explanation = ExplainabilityEngine().explain(decision, expense, session)

        return JSONResponse(status_code=status.HTTP_200_OK, content=explanation)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/metrics")
async def get_metrics():
    """Retrieve Prometheus metrics."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
