import datetime
import uuid

from app.report_generator import generate_csv_report, generate_markdown_report
from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import AgentResult, WorkflowContext
from domain.expense import Expense
from domain.report import Report


@capability(
    name="report_agent",
    version="1.0.0",
    inputs=["receipt", "policy_res", "fraud_res", "validation_errors"],
    outputs=["report"],
)
class ReportAgent(BaseAgent):
    """Report Agent generates final reports in Markdown or CSV formats."""

    def execute(self, context: WorkflowContext) -> AgentResult:
        self.logger.info("Report Agent generating output reports.")

        # 1. Retrieve elements from context/metadata
        receipt = context.get("receipt")
        policy_res = context.get("policy_res")
        fraud_res = context.get("fraud_res")
        validation_errors = context.get("validation_errors", [])

        # Convert policy_res to dict if it's a PolicyResult object
        if hasattr(policy_res, "model_dump"):
            policy_res_dict = policy_res.model_dump()
        elif isinstance(policy_res, dict):
            policy_res_dict = policy_res
        else:
            policy_res_dict = {}

        # Pull reflection details
        reflection_critique = context.metadata.get("reflection_critique")
        needs_review = context.metadata.get("needs_human_review", False)
        review_reason = context.metadata.get("human_review_reason")

        # Map details for report structure
        merchant = receipt.merchant_name if receipt else "Unknown"
        amount = receipt.amount if receipt else 0.0
        currency = receipt.currency if receipt else "USD"
        date_val = receipt.date if receipt else "Unknown"

        is_approved = not validation_errors
        if policy_res_dict and policy_res_dict.get("violations"):
            is_approved = False
        if fraud_res and fraud_res.score > 0.7:
            is_approved = False

        status_str = "APPROVED" if is_approved and not needs_review else "REJECTED"

        # Build domain Expense model
        expense_obj = Expense(
            id=str(uuid.uuid4()),
            employee_id=context.metadata.get("employee_id", "EMP-001"),
            merchant=merchant,
            amount=amount,
            currency=currency,
            date=date_val,
            category=getattr(receipt, "category", "Other") if receipt else "Other",
        )

        # 2. Build explanation summary
        summary_lines = []
        if is_approved:
            summary_lines.append("Expense complies with all policy checks.")
        else:
            summary_lines.append("Expense flagged for rejection.")

        if policy_res_dict and policy_res_dict.get("violations"):
            summary_lines.append(f"Policy violations found: {', '.join(policy_res_dict['violations'])}")
        if fraud_res and fraud_res.indicators:
            summary_lines.append(f"Fraud flags: {', '.join(fraud_res.indicators)}")
        if needs_review:
            summary_lines.append(f"Escalated to human review: {review_reason}")
        if reflection_critique:
            summary_lines.append(f"Critique: {reflection_critique}")

        summary = "\n".join(summary_lines)

        # 3. Generate outputs
        report_format = context.metadata.get("report_format", "markdown").lower()

        claimed = receipt.amount if receipt else 0.0
        reimbursable = policy_res_dict.get("reimbursable_amount", claimed) if policy_res_dict else claimed
        rejected = policy_res_dict.get("rejected_amount", 0.0) if policy_res_dict else 0.0
        fraud_score = int(fraud_res.score * 100) if fraud_res else 0
        violations = policy_res_dict.get("violations", []) if policy_res_dict else []

        expense_item = {
            "merchant": merchant,
            "date": date_val,
            "category": expense_obj.category,
            "amount": amount,
            "reimbursable": reimbursable,
            "rejected": rejected,
            "fraud_score": fraud_score,
            "fraud_reason": fraud_res.explanation if fraud_res else "",
            "status": status_str,
            "violations": violations,
        }

        audit_result = {
            "expenses": [expense_item],
            "total_claimed": amount,
            "total_reimbursable": reimbursable,
            "total_rejected": rejected,
            "currency": currency,
            "compliance_score": max(0.0, min(100.0, 100.0 - (10.0 * len(violations)) - (fraud_score * 0.5))),
            "decision": status_str,
            "reasoning": summary,
        }

        if report_format == "csv":
            report_content = generate_csv_report(audit_result)
        else:
            report_content = generate_markdown_report(audit_result)

        # 4. Save and return report
        report = Report(
            id=str(uuid.uuid4()),
            audit_id=context.metadata.get("audit_id", str(uuid.uuid4())),
            created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            format=report_format,
            content=report_content,
            status="APPROVED" if is_approved and not needs_review else "REJECTED",
        )

        context.metadata["report"] = report.model_dump()
        context.metadata["response"] = summary

        return AgentResult(status="SUCCESS", output=report, confidence=1.0, explanation=summary)
