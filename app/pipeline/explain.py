from typing import Any


class ExplainabilityEngine:
    """Generate human‑readable explanation for audit decision.

    The engine receives the decision dictionary produced by DecisionEngine, the original expense object, and an optional session context. It returns a JSON‑serialisable dictionary.
    """

    def explain(self, decision: dict[str, Any], expense: Any, session: Any = None) -> dict[str, Any]:
        explanation = {
            "audit_id": decision.get("audit_id"),
            "decision": decision.get("decision"),
            "confidence": decision.get("confidence"),
            "reasons": decision.get("reasons", {}),
        }
        summary_parts = []
        if explanation["decision"] == "approved":
            summary_parts.append("✅ Expense approved")
        else:
            summary_parts.append("❌ Expense rejected")
        fraud = decision.get("reasons", {}).get("fraud")
        if fraud:
            score = fraud.get("fraud_score")
            if score is not None:
                summary_parts.append(f"Fraud score: {score:.2f}")
            else:
                # If fraud is a dict of boolean flags, report active flags
                active_flags = [k for k, v in fraud.items() if v]
                if active_flags:
                    summary_parts.append(f"Fraud indicators: {', '.join(active_flags)}")
                else:
                    summary_parts.append("Fraud check triggered")
        policy = decision.get("reasons", {}).get("policy")
        if policy:
            policy_dec = policy.get("policy_decision")
            summary_parts.append(f"Policy decision: {policy_dec}")
        explanation["summary"] = ", ".join(summary_parts)
        expense_info = {
            "employee_id": getattr(expense, "employee_id", None),
            "merchant": getattr(expense, "merchant", None),
            "amount": getattr(expense, "amount", None),
            "currency": getattr(expense, "currency", None),
            "date": getattr(expense, "date", None).isoformat() if getattr(expense, "date", None) else None,
        }
        explanation["expense"] = expense_info
        return explanation
