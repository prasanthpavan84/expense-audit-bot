import uuid
from datetime import datetime
from core.agents.base_agent import BaseAgent
from core.metadata.capability import capability
from core.validation.schemas import WorkflowContext, AgentResult
from domain.report import Report
from domain.expense import Expense
from app.report_generator import generate_markdown_report, generate_csv_report


@capability(
    name="report_agent",
    version="1.0.0",
    inputs=["receipt", "policy_res", "fraud_res", "validation_errors"],
    outputs=["report"]
)
class ReportAgent(BaseAgent):
    """Report generation agent compiling audit outcomes into a structured Report."""

    def initialize(self) -> None:
        super().initialize()
        self.logger.info("Report agent initialized.")

    def execute(self, context: WorkflowContext) -> AgentResult:
        receipt = context.receipt
        policy_res = context.policy_res
        fraud_res = context.fraud_res
        validation_errors = context.metadata.get("validation_errors", [])

        # Construct pure Domain Expense model
        expense_id = str(uuid.uuid4())
        
        is_approved = True
        violations = []
        
        if validation_errors:
            is_approved = False
            violations.extend(validation_errors)
        
        if policy_res:
            violations.extend(policy_res.violations)
            if not policy_res.is_compliant:
                is_approved = False

        if fraud_res:
            if fraud_res.score > 0.7:
                is_approved = False
                violations.append(f"High fraud risk ({fraud_res.score:.2f})")

        category = "Other"
        if receipt:
            if hasattr(receipt, "category") and receipt.category:
                category = receipt.category
            else:
                merchant_lower = receipt.merchant_name.lower()
                text_lower = receipt.raw_text.lower() if receipt.raw_text else ""
                if "meal" in text_lower or "food" in text_lower or "starbucks" in merchant_lower:
                    category = "Meals"
                elif "hotel" in text_lower or "stay" in text_lower or "hilton" in merchant_lower:
                    category = "Hotel"
                elif "uber" in merchant_lower or "taxi" in merchant_lower or "ride" in merchant_lower:
                    category = "Taxi"
                elif "flight" in text_lower:
                    category = "Flight"
                elif "software" in text_lower:
                    category = "Software"

        expense = Expense(
            id=expense_id,
            employee_id="EMP102",  # Default test employee
            merchant=receipt.merchant_name if receipt else "Unknown",
            date=receipt.date if receipt else "Unknown",
            amount=receipt.amount if receipt else 0.0,
            currency=receipt.currency if receipt else "USD",
            category=category,
            items=receipt.items if receipt else [],
            justification=context.input,
            policy_result=policy_res,
            fraud_result=fraud_res
        )

        total_claimed = expense.amount
        total_reimbursable = expense.amount if is_approved else 0.0
        total_rejected = 0.0 if is_approved else expense.amount

        # Standard dictionary format for report generator integration
        exp_dict = expense.model_dump()
        exp_dict["is_approved"] = is_approved
        exp_dict["fraud_score"] = (fraud_res.score * 100) if fraud_res else 0.0
        exp_dict["fraud_reason"] = "High Risk" if (fraud_res and fraud_res.score > 0.7) else ""
        exp_dict["violations"] = violations
        exp_dict["reimbursable"] = total_reimbursable
        exp_dict["rejected"] = total_rejected
        exp_dict["status"] = "Approved" if is_approved else "Rejected"

        audit_result = {
            "expenses": [exp_dict],
            "total_claimed": total_claimed,
            "total_reimbursable": total_reimbursable,
            "total_rejected": total_rejected,
            "currency": expense.currency,
            "compliance_score": 100.0 if is_approved else 0.0
        }

        report_format = context.metadata.get("report_format", "markdown")
        if report_format == "csv":
            summary = generate_csv_report(audit_result)
        else:
            summary = generate_markdown_report(audit_result)

        report = Report(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow().isoformat(),
            expenses=[expense],
            summary=summary,
            status="APPROVED" if is_approved else "REJECTED"
        )

        return AgentResult(
            status="SUCCESS",
            output=report,
            confidence=1.0,
            explanation="Report generated successfully."
        )
