import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app.core.config_manager import config
from app.workflow.engine.workflow_engine import WorkflowEngine


class Evaluator:
    """Runs evaluations over the 500-case dataset, computing accuracy, latency, and costs."""

    def __init__(self):
        self.engine = WorkflowEngine()
        self.base_dir = Path(__file__).resolve().parent / "datasets"
        self.reports_dir = Path(__file__).resolve().parent / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def load_expected_results(self) -> dict[str, Any]:
        expected_file = self.base_dir / "expected_results.json"
        if not expected_file.exists():
            return {}
        with open(expected_file, encoding="utf-8") as f:
            return json.load(f)

    async def run_evaluation(self, max_cases: int = 500) -> dict[str, Any]:
        expected = self.load_expected_results()
        if not expected:
            print("No expected results found. Run generate_dataset.py first.")
            return {}

        results = []
        total_cases = 0
        correct_decisions = 0

        # Track true positives, false positives, false negatives for Fraud classification
        tp, fp, fn, tn = 0, 0, 0, 0

        start_time = time.time()

        # Categories to process
        folders = ["normal", "fraud", "policy", "ocr", "currency", "edge"]

        for folder in folders:
            folder_path = self.base_dir / folder
            if not folder_path.exists():
                continue

            for file in folder_path.glob("*.txt"):
                if total_cases >= max_cases:
                    break

                case_id = file.stem
                expected_info = expected.get(case_id)
                if not expected_info:
                    continue

                with open(file, encoding="utf-8") as f:
                    content = f.read()

                # Execute workflow
                start_case = time.time()
                try:
                    ctx = await self.engine.execute_workflow(
                        workflow_name="AUDIT",
                        raw_input=content,
                        audit_id=case_id,
                        correlation_id=f"corr-{case_id}",
                        user_role="Associate",
                    )
                    latency = time.time() - start_case

                    # Read final status
                    needs_review = ctx.metadata.get("needs_human_review", False)
                    violations = ctx.metadata.get("policy_violations", [])

                    status = "Approved"
                    if violations:
                        status = "Rejected"
                    if needs_review:
                        status = "Needs Human Review"

                    exp_status = expected_info["expected_status"]
                    is_correct = status == exp_status
                    if is_correct:
                        correct_decisions += 1

                    # Track binary classification metrics for fraud (Rejected/Needs Review vs Approved)
                    is_anomaly = status in ["Rejected", "Needs Human Review"]
                    exp_anomaly = exp_status in ["Rejected", "Needs Human Review"]

                    if is_anomaly and exp_anomaly:
                        tp += 1
                    elif is_anomaly and not exp_anomaly:
                        fp += 1
                    elif not is_anomaly and exp_anomaly:
                        fn += 1
                    else:
                        tn += 1

                    results.append(
                        {
                            "case_id": case_id,
                            "category": folder,
                            "expected": exp_status,
                            "actual": status,
                            "correct": is_correct,
                            "latency_sec": latency,
                        }
                    )
                    total_cases += 1

                except Exception as e:
                    print(f"Error running case {case_id}: {e}")

        total_time = time.time() - start_time
        avg_latency = total_time / total_cases if total_cases > 0 else 0.0
        accuracy = correct_decisions / total_cases if total_cases > 0 else 0.0

        # Precision & Recall calculations
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Cost estimation: mock is free, gemini is cheap
        cost_per_case = 0.0 if config.model == "mock" else 0.00015
        total_cost = total_cases * cost_per_case

        metrics = {
            "model_used": config.model,
            "total_cases": total_cases,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "total_time_sec": round(total_time, 2),
            "avg_latency_sec": round(avg_latency, 3),
            "estimated_cost_usd": round(total_cost, 4),
            "success_rate": round(correct_decisions / total_cases, 4) if total_cases > 0 else 1.0,
        }

        # Export reports
        self.export_reports(metrics, results)
        return metrics

    def export_reports(self, metrics: dict[str, Any], results: list[dict[str, Any]]):
        # 1. JSON Report
        json_path = self.reports_dir / "benchmark.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"metrics": metrics, "runs": results}, f, indent=2)

        # 2. Markdown Report
        md_path = self.reports_dir / "benchmark.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Benchmark Evaluation Report\n\n")
            f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
            f.write("## Overall Metrics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|---|---|\n")
            f.write(f"| **Model Used** | `{metrics['model_used']}` |\n")
            f.write(f"| **Total Cases** | {metrics['total_cases']} |\n")
            f.write(f"| **Accuracy** | {metrics['accuracy'] * 100:.2f}% |\n")
            f.write(f"| **Precision** | {metrics['precision'] * 100:.2f}% |\n")
            f.write(f"| **Recall** | {metrics['recall'] * 100:.2f}% |\n")
            f.write(f"| **F1 Score** | {metrics['f1_score'] * 100:.2f}% |\n")
            f.write(f"| **Total Duration** | {metrics['total_time_sec']} seconds |\n")
            f.write(f"| **Avg Latency** | {metrics['avg_latency_sec']} seconds |\n")
            f.write(f"| **Total Cost** | ${metrics['estimated_cost_usd']:.4f} USD |\n")

        print(f"Benchmark reports generated successfully in {self.reports_dir}")


if __name__ == "__main__":
    evaluator = Evaluator()
    asyncio.run(evaluator.run_evaluation())
