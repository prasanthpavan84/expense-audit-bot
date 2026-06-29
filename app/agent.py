# ruff: noqa
import datetime
import json
import re
from pydantic import BaseModel, Field
from typing import List, Optional

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.workflow import Workflow, START, node
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.genai import types

from app.config import config

# Initialize model
model = Gemini(
    model=config.model,
    retry_options=types.HttpRetryOptions(attempts=config.max_iterations),
)

# -----------------------------------------------------------------------------
# Logging Helper
# -----------------------------------------------------------------------------
def log_audit(event_type: str, severity: str, details: dict):
    """Write structured JSON audit log."""
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "severity": severity,
        **details
    }
    print(f"AUDIT_LOG: {json.dumps(log_entry)}")

# -----------------------------------------------------------------------------
# MCP Toolset Configuration
# -----------------------------------------------------------------------------
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "app.mcp_server"],
        ),
    )
)

# -----------------------------------------------------------------------------
# Structured Schemas
# -----------------------------------------------------------------------------
class ExpenseDetails(BaseModel):
    merchant: str = Field(description="The name of the merchant/vendor.")
    date: str = Field(description="The date of the expense in YYYY-MM-DD format.")
    amount: float = Field(description="The total amount of the expense.")
    currency: str = Field(description="The currency code (e.g. USD, EUR, INR).")
    category: str = Field(description="The category of the expense (e.g. Meals, Travel, Software, Restricted).")
    items: List[str] = Field(description="List of individual items purchased.")

class PolicyVerification(BaseModel):
    compliant: bool = Field(description="True if the expense complies with all policies, False otherwise.")
    violations: List[str] = Field(description="List of specific policy violations found (empty if compliant).")
    audit_notes: str = Field(description="Detailed notes explaining the compliance check.")

# -----------------------------------------------------------------------------
# Sub-Agents
# -----------------------------------------------------------------------------
receipt_extractor = Agent(
    name="receipt_extractor",
    model=model,
    instruction="""You are a Receipt Extractor agent.
Analyze the user's input (receipt text, description, or details) and extract:
- merchant
- date (YYYY-MM-DD)
- amount (float)
- currency (3-letter code)
- category (Meals, Travel, Software, Restricted, or Other)
- items (list of strings)

You have access to the MCP tools:
- Use get_exchange_rate to convert amounts to USD if the expense is in a different currency.
- Use check_vendor_restrictions to see if the vendor name is restricted.

Ensure all fields are populated accurately. If a field is missing, make a best estimate or put 'Unknown'.""",
    output_schema=ExpenseDetails,
    tools=[mcp_toolset],
)

# Calculate today's date dynamically
today_str = datetime.date.today().isoformat()

policy_verifier = Agent(
    name="policy_verifier",
    model=model,
    instruction=f"""You are a Policy Verifier agent.
Compare the provided expense details against the company's expense policies.
Current date (today) is {today_str}.

You must use the following MCP tools to verify compliance:
- Use get_corporate_limits to get the latest corporate spending policy limits for meals, travel, and software.
- Use get_exchange_rate to convert any non-USD amounts to USD before checking limits.
- Use check_vendor_restrictions to verify if the merchant/vendor is restricted.

Check each rule and return:
- compliant: true if all rules pass, false if any rule is violated.
- violations: list of specific policy violations.
- audit_notes: detailed notes explaining your checks and any conversion rates or limits fetched.

Note: If the currency is not USD, convert it to USD before applying the limit check, and document the conversion in audit_notes.""",
    output_schema=PolicyVerification,
    tools=[mcp_toolset],
)

# -----------------------------------------------------------------------------
# Orchestrator Agent
# -----------------------------------------------------------------------------
audit_orchestrator = Agent(
    name="audit_orchestrator",
    model=model,
    instruction="""You are the Expense Audit Orchestrator.
Your goal is to coordinate the audit of a user-submitted expense.
Always follow this workflow:
1. Call the receipt_extractor tool to extract structured details from the user's input.
2. Call the policy_verifier tool to verify if the extracted details comply with corporate policy.
3. Determine the final decision:
   - If the expense is fully compliant and the amount is under $200, output 'APPROVED'.
   - If there are policy violations (e.g. restricted items, over limits), output 'DENIED' with the specific reasons.
   - If the expense is compliant but the total amount is high (amount >= $200), or if there is any ambiguity, output 'NEEDS_REVIEW' to escalate for human approval.
Provide a clear, detailed explanation of your decision and the findings from your sub-agents.""",
    tools=[AgentTool(receipt_extractor), AgentTool(policy_verifier)],
)

# -----------------------------------------------------------------------------
# Workflow Nodes
# -----------------------------------------------------------------------------
def security_checkpoint(ctx: Context, node_input: types.Content) -> Event:
    """Security checkpoint checking for PII, prompt injections, and prohibited words."""
    text = ""
    for part in node_input.parts:
        if part.text:
            text += part.text
            
    # PII Scrubbing
    scrubbed_text = text
    pii_found = []
    
    # 1. Credit Cards
    cc_regex = r"\b(?:\d[ -]*?){13,16}\b"
    if re.search(cc_regex, scrubbed_text):
        scrubbed_text = re.sub(cc_regex, "[REDACTED_CREDIT_CARD]", scrubbed_text)
        pii_found.append("credit_card")
        
    # 2. Email Address
    email_regex = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    if re.search(email_regex, scrubbed_text):
        scrubbed_text = re.sub(email_regex, "[REDACTED_EMAIL]", scrubbed_text)
        pii_found.append("email")
        
    # 3. Social Security Number
    ssn_regex = r"\b\d{3}-\d{2}-\d{4}\b"
    if re.search(ssn_regex, scrubbed_text):
        scrubbed_text = re.sub(ssn_regex, "[REDACTED_SSN]", scrubbed_text)
        pii_found.append("ssn")

    # Prompt Injection Detection
    injection_keywords = ["ignore previous instructions", "system prompt", "you are now", "override policy", "jailbreak", "dan mode"]
    injection_detected = False
    matched_keyword = None
    for keyword in injection_keywords:
        if keyword in text.lower():
            injection_detected = True
            matched_keyword = keyword
            break
            
    # Domain-specific rule (prohibited purchase terms)
    prohibited_keywords = ["bribe", "kickback", "payoff", "ransom"]
    prohibited_detected = False
    matched_prohibited = None
    for keyword in prohibited_keywords:
        if keyword in text.lower():
            prohibited_detected = True
            matched_prohibited = keyword
            break

    # Decision and Logging
    if injection_detected:
        log_audit(
            event_type="prompt_injection_blocked",
            severity="CRITICAL",
            details={
                "matched_keyword": matched_keyword,
                "pii_scrubbed": pii_found,
                "session_id": ctx.session.id
            }
        )
        return Event(
            output="CRITICAL: Prompt injection attempt detected and blocked.",
            route="security_event",
            content=types.Content(
                role='model',
                parts=[types.Part.from_text(text="**SECURITY ERROR**: Expense submission blocked due to prompt injection warning.")]
            )
        )
        
    if prohibited_detected:
        log_audit(
            event_type="prohibited_content_blocked",
            severity="WARNING",
            details={
                "matched_prohibited": matched_prohibited,
                "pii_scrubbed": pii_found,
                "session_id": ctx.session.id
            }
        )
        return Event(
            output=f"DENIED: Prohibited term '{matched_prohibited}' found in submission.",
            route="security_event",
            content=types.Content(
                role='model',
                parts=[types.Part.from_text(text=f"**AUDIT BLOCK**: Prohibited term '{matched_prohibited}' found. Action blocked.")]
            )
        )

    # Normal Flow
    severity = "WARNING" if pii_found else "INFO"
    log_audit(
        event_type="input_verified",
        severity=severity,
        details={
            "pii_scrubbed": pii_found,
            "session_id": ctx.session.id,
            "input_length": len(text)
        }
    )
    
    return Event(
        output=scrubbed_text,
        content=types.Content(role='user', parts=[types.Part.from_text(text=scrubbed_text)])
    )

def route_decision(ctx: Context, node_input: types.Content) -> Event:
    """Routes the workflow based on the orchestrator's decision."""
    text = ""
    for part in node_input.parts:
        if part.text:
            text += part.text
            
    text_lower = text.lower()
    if "needs_review" in text_lower or "needs review" in text_lower or "needs_review" in text_lower:
        return Event(output=text, route="needs_review", state={"orchestrator_decision": text})
    elif "denied" in text_lower or "reject" in text_lower:
        return Event(output=text, route="denied", state={"orchestrator_decision": text})
    else:
        return Event(output=text, route="approved", state={"orchestrator_decision": text})

async def human_review(ctx: Context, node_input: str):
    """Asks for human approval if the orchestrator requests review."""
    if not ctx.resume_inputs or "approver_decision" not in ctx.resume_inputs:
        yield RequestInput(
            interrupt_id="approver_decision",
            message=f"Expense needs human review. Orchestrator analysis:\n{node_input}\n\nShould this expense be approved? (Type 'approve' or 'deny' with comments)"
        )
        return
    
    decision = ctx.resume_inputs["approver_decision"]
    yield Event(output=f"Human Review Outcome: {decision}", state={"approver_decision": decision})

def finalize_expense(ctx: Context, node_input: str):
    """Generates the final report and output for the user."""
    final_status = "Approved"
    
    if "approver_decision" in ctx.state:
        decision = ctx.state["approver_decision"].lower()
        if "deny" in decision or "reject" in decision:
            final_status = "Denied by Auditor"
        else:
            final_status = "Approved by Auditor"
    else:
        # Check decision in state or predecessor input
        decision_text = ctx.state.get("orchestrator_decision", node_input).lower()
        if "denied" in decision_text or "reject" in decision_text or "blocked" in decision_text:
            final_status = "Denied / Blocked"
        else:
            final_status = "Approved (Auto)"
            
    summary_msg = f"### EXPENSE AUDIT FINAL REPORT\n\n**Status**: {final_status}\n\n**Details & Findings**:\n{node_input}"
    
    yield Event(
        content=types.Content(
            role='model',
            parts=[types.Part.from_text(text=summary_msg)]
        )
    )
    yield Event(output=summary_msg)

# -----------------------------------------------------------------------------
# Workflow Graph
# -----------------------------------------------------------------------------
root_agent = Workflow(
    name="expense_audit_workflow",
    edges=[
        (START, security_checkpoint),
        (security_checkpoint, {"__DEFAULT__": audit_orchestrator, "security_event": finalize_expense}),
        (audit_orchestrator, route_decision),
        (route_decision, {"needs_review": human_review, "__DEFAULT__": finalize_expense}),
        (human_review, finalize_expense),
    ],
    description="An end-to-end expense report auditing workflow with automated compliance checking and human-in-the-loop escalation."
)

app = App(
    root_agent=root_agent,
    name="app",
)
