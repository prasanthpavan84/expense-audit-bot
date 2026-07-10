import statistics
from typing import Any


class EvaluationMetrics:
    @staticmethod
    def calculate_ocr_accuracy(predictions: list[dict[str, Any]], targets: list[dict[str, Any]]) -> float:
        """Calculates accuracy of OCR field extraction (merchant, date, amount, currency)."""
        if not predictions or not targets:
            return 0.0

        correct = 0
        total = 0

        for p, t in zip(predictions, targets):
            # Fields to compare
            for field in ["merchant", "date", "amount", "currency"]:
                t_val = t.get(f"expected_{field}")
                if t_val is None:
                    continue

                # Retrieve from state or direct prediction
                p_val = p.get(field)
                if p_val is None and "state" in p:
                    # Look inside state audited expenses
                    expenses = p["state"].get("audited_expenses", [])
                    if expenses:
                        p_val = expenses[0].get(field)

                if p_val is not None:
                    # Normalize for comparison
                    if isinstance(t_val, float) or isinstance(p_val, float):
                        try:
                            if abs(float(p_val) - float(t_val)) < 0.01:
                                correct += 1
                        except (ValueError, TypeError):
                            pass
                    else:
                        if str(p_val).strip().lower() == str(t_val).strip().lower():
                            correct += 1
                total += 1

        return correct / total if total > 0 else 1.0

    @staticmethod
    def calculate_policy_accuracy(predictions: list[dict[str, Any]], targets: list[dict[str, Any]]) -> float:
        """Calculates policy compliance decision accuracy."""
        if not predictions or not targets:
            return 0.0

        correct = 0
        total = 0

        for p, t in zip(predictions, targets):
            t_val = t.get("expected_compliant") or t.get("expected_decision")
            if t_val is None:
                continue

            p_val = None
            if "state" in p:
                p_val = p["state"].get("orchestrator_decision")
            if p_val is None:
                p_val = p.get("decision")

            if p_val is not None and t_val is not None:
                # Normalize values
                p_norm = (
                    "approved"
                    if "approve" in str(p_val).lower()
                    else "denied" if "deni" in str(p_val).lower() else "review"
                )
                t_norm = (
                    "approved"
                    if "approve" in str(t_val).lower() or str(t_val).lower() == "true"
                    else "denied" if "deni" in str(t_val).lower() or str(t_val).lower() == "false" else "review"
                )

                if p_norm == t_norm:
                    correct += 1
            total += 1

        return correct / total if total > 0 else 1.0

    @staticmethod
    def calculate_fraud_accuracy(predictions: list[dict[str, Any]], targets: list[dict[str, Any]]) -> float:
        """Calculates fraud detection accuracy."""
        if not predictions or not targets:
            return 0.0

        correct = 0
        total = 0

        for p, t in zip(predictions, targets):
            t_val = t.get("expected_is_fraud") or t.get("expected_fraud_score")
            if t_val is None:
                continue

            p_val = None
            if "state" in p:
                expenses = p["state"].get("audited_expenses", [])
                if expenses:
                    # Fraud if score > 0 or specific reason exists
                    p_val = expenses[0].get("fraud_score", 0) > 0

            if p_val is None:
                p_val = p.get("is_fraud", False)

            # Normalize targets
            t_bool = (
                bool(t_val) if isinstance(t_val, bool) or str(t_val).lower() in ["true", "false"] else int(t_val) > 0
            )

            if bool(p_val) == t_bool:
                correct += 1
            total += 1

        return correct / total if total > 0 else 1.0

    @staticmethod
    def calculate_overall_accuracy(predictions: list[dict[str, Any]], targets: list[dict[str, Any]]) -> float:
        """Calculates overall decision accuracy (perfect match of decisions)."""
        if not predictions or not targets:
            return 0.0

        correct = 0
        total = 0

        for p, t in zip(predictions, targets):
            t_val = t.get("expected_decision") or t.get("expected_compliant")
            if t_val is None:
                continue

            p_val = p.get("passed")  # If evaluation checker marked it as passed
            if p_val is not None:
                if bool(p_val):
                    correct += 1
            else:
                p_dec = p.get("state", {}).get("orchestrator_decision")
                if p_dec and str(p_dec).strip().lower() == str(t_val).strip().lower():
                    correct += 1
            total += 1

        return correct / total if total > 0 else 1.0

    @staticmethod
    def calculate_latency_stats(latencies: list[float]) -> dict[str, float]:
        """Calculates average and percentile latency values."""
        if not latencies:
            return {"avg": 0.0, "p95": 0.0}

        avg = statistics.mean(latencies)
        sorted_lats = sorted(latencies)
        p95_idx = int(len(sorted_lats) * 0.95)
        p95 = sorted_lats[min(p95_idx, len(sorted_lats) - 1)]

        return {"avg": round(avg, 3), "p95": round(p95, 3)}

    @staticmethod
    def calculate_completion_rates(results: list[dict[str, Any]]) -> dict[str, float]:
        """Calculates failure rate and success rate of executions."""
        if not results:
            return {"success_rate": 0.0, "failure_rate": 0.0}

        failures = sum(1 for r in results if r.get("errors") or "NotImplementedError" in str(r.get("errors", "")))
        total = len(results)

        failure_rate = failures / total
        success_rate = 1.0 - failure_rate

        return {"success_rate": round(success_rate, 4), "failure_rate": round(failure_rate, 4)}
