import pytest

from app.agent import finalize_expense, intent_router


class MockContext:
    def __init__(self, session_id="test_sess"):
        self.session = type("DummySession", (), {"id": session_id})()
        self.state = {}


@pytest.mark.asyncio
async def test_intent_router_hybrid():
    # Fuzzy policy question
    ctx = MockContext(session_id="test_sess_1")
    evt = await intent_router(ctx, "Explain corporate limits for meals")
    assert evt.actions.route == "POLICY"
    assert ctx.state["flow_intent"] == "POLICY"


@pytest.mark.asyncio
async def test_dpl_fraud_escalation():
    # High fraud score triggers Needs Human Review via DPL
    ctx = MockContext(session_id="test_sess_2")
    ctx.state["audited_expenses"] = [
        {
            "merchant": "Subway",
            "date": "2026-06-25",
            "amount": 15.50,
            "currency": "USD",
            "category": "Meals",
            "reimbursable": 15.50,
            "rejected": 0.0,
            "fraud_score": 85.0,  # Exceeds 80
            "fraud_reason": "High fraud score detected.",
            "status": "Approved",
            "violations": [],
        }
    ]

    evt_list = []
    for evt in finalize_expense(ctx, "Formatted Report"):
        evt_list.append(evt)

    assert ctx.state["orchestrator_decision"] == "Needs Human Review"
    # Verify HITL reason
    assert "Fraud score (85) exceeds threshold (> 80.0)" in ctx.state["formatted_response"]


@pytest.mark.asyncio
async def test_dpl_policy_rejection():
    # Policy violation causes rejection via DPL
    ctx = MockContext(session_id="test_sess_3")
    ctx.state["audited_expenses"] = [
        {
            "merchant": "Casino Club",
            "date": "2026-06-25",
            "amount": 100.00,
            "currency": "USD",
            "category": "Other",
            "reimbursable": 0.0,
            "rejected": 100.00,
            "fraud_score": 40.0,
            "fraud_reason": "Restricted vendor.",
            "status": "Rejected",
            "violations": ["Prohibited restricted vendor Casino Club"],
        }
    ]

    evt_list = []
    for evt in finalize_expense(ctx, "Formatted Report"):
        evt_list.append(evt)

    assert ctx.state["orchestrator_decision"] == "Denied"


@pytest.mark.asyncio
async def test_dpl_confidence_escalation():
    # Low confidence score (< 0.65) triggers Needs Human Review via DPL
    ctx = MockContext(session_id="test_sess_4")
    ctx.state["ocr_confidence_score"] = 0.50  # Low OCR confidence
    ctx.state["intent_confidence"] = 0.90
    ctx.state["audited_expenses"] = [
        {
            "merchant": "Subway",
            "date": "2026-06-25",
            "amount": 15.50,
            "currency": "USD",
            "category": "Meals",
            "reimbursable": 15.50,
            "rejected": 0.0,
            "fraud_score": 0.0,
            "fraud_reason": "No anomalies.",
            "status": "Approved",
            "violations": [],
            "merchant_provenance": {"confidence": 0.90},
            "date_provenance": {"confidence": 0.90},
            "amount_provenance": {"confidence": 0.90},
            "currency_provenance": {"confidence": 0.90},
        }
    ]

    evt_list = []
    for evt in finalize_expense(ctx, "Formatted Report"):
        evt_list.append(evt)

    assert ctx.state["orchestrator_decision"] == "Needs Human Review"


@pytest.mark.asyncio
async def test_schema_format_healing():
    # Healing missing JSON block
    ctx = MockContext(session_id="test_sess_5")
    ctx.state["audited_expenses"] = [
        {
            "merchant": "Subway",
            "date": "2026-06-25",
            "amount": 15.50,
            "currency": "USD",
            "category": "Meals",
            "reimbursable": 15.50,
            "rejected": 0.0,
            "fraud_score": 0.0,
            "fraud_reason": "None.",
            "status": "Approved",
            "violations": [],
        }
    ]

    evt_list = []
    for evt in finalize_expense(ctx, "Raw text without json block"):
        evt_list.append(evt)

    final_output = evt_list[-1].output
    assert "```json" in final_output
