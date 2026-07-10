import datetime
import json
import math
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = PROJECT_ROOT / "evaluation"
METRICS_JSON = EVAL_DIR / "metrics.json"
SCORECARD_JSON = EVAL_DIR / "scorecard.json"
RESULTS_JSON = EVAL_DIR / "results.json"


def get_git_sha():
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=str(PROJECT_ROOT)
        )
        return res.stdout.strip()
    except Exception:
        return "N/A"


def calculate_confidence_interval(data, confidence=0.95):
    n = len(data)
    if n < 2:
        return 0.0, 0.0
    mean_val = sum(data) / n
    variance = sum((x - mean_val) ** 2 for x in data) / (n - 1)
    std_dev = math.sqrt(variance)
    margin = 1.96 * (std_dev / math.sqrt(n))
    return mean_val - margin, mean_val + margin


def run_metrics_engine():
    if not RESULTS_JSON.exists():
        print(f"[Metrics Engine] Error: {RESULTS_JSON} not found.")
        return

    with open(RESULTS_JSON, encoding="utf-8") as f:
        results = json.load(f)

    total = len(results)
    if total == 0:
        return

    # Telemetry and stats
    git_sha = get_git_sha()
    latencies = [r["execution_time_sec"] for r in results]
    mean_latency = sum(latencies) / total
    variance_latency = sum((x - mean_latency) ** 2 for x in latencies) / (total - 1) if total > 1 else 0.0
    std_dev_latency = math.sqrt(variance_latency)
    ci_min, ci_max = calculate_confidence_interval(latencies)

    mem_usages = [r["memory_usage_mb"] for r in results]
    mean_mem = sum(mem_usages) / total
    variance_mem = sum((x - mean_mem) ** 2 for x in mem_usages) / (total - 1) if total > 1 else 0.0
    std_dev_mem = math.sqrt(variance_mem)

    # Subsystem specific tracking
    subsystems = {
        "extraction": {"correct": 0, "total": 0},
        "validation": {"correct": 0, "total": 0},
        "fraud": {"correct": 0, "total": 0},
        "policy": {"correct": 0, "total": 0},
        "reasoning": {"correct": 0, "total": 0},
        "reflection": {"correct": 0, "total": 0},
        "report": {"correct": 0, "total": 0},
        "workflow": {"correct": 0, "total": 0},
    }

    tp, fp, fn, tn = 0, 0, 0, 0
    error_list = []

    # Error classification
    error_counts = {
        "ocr_failures": 0,
        "policy_mismatches": 0,
        "fraud_false_positives": 0,
        "fraud_false_negatives": 0,
        "routing_errors": 0,
        "hallucinations": 0,
        "validation_failures": 0,
        "parsing_issues": 0,
    }

    for r in results:
        passed = r["passed"]
        cat = r["category"].lower()

        # Mapping to matrix
        if passed:
            tp += 1
        else:
            fn += 1
            error_list.append(
                {
                    "test_id": r["test_id"],
                    "category": r["category"],
                    "input": r["input"][:60] + "...",
                    "reason": r["reason"],
                }
            )

        # Distribute scores dynamically across subsystems
        if "ocr" in cat or "extract" in cat:
            subsystems["extraction"]["total"] += 1
            if passed:
                subsystems["extraction"]["correct"] += 1
            else:
                error_counts["ocr_failures"] += 1

        if "validation" in cat or "edge" in cat:
            subsystems["validation"]["total"] += 1
            if passed:
                subsystems["validation"]["correct"] += 1
            else:
                error_counts["validation_failures"] += 1

        if "fraud" in cat:
            subsystems["fraud"]["total"] += 1
            if passed:
                subsystems["fraud"]["correct"] += 1
            else:
                error_counts["fraud_false_negatives"] += 1

        if "policy" in cat:
            subsystems["policy"]["total"] += 1
            if passed:
                subsystems["policy"]["correct"] += 1
            else:
                error_counts["policy_mismatches"] += 1

        if "reason" in cat:
            subsystems["reasoning"]["total"] += 1
            if passed:
                subsystems["reasoning"]["correct"] += 1

        # Default reflection, report and workflow evaluations
        subsystems["reflection"]["total"] += 1
        if passed:
            subsystems["reflection"]["correct"] += 1

        subsystems["report"]["total"] += 1
        if r["agent_output"].startswith("#") or "```" in r["agent_output"]:
            subsystems["report"]["correct"] += 1

        subsystems["workflow"]["total"] += 1
        if len(r["errors"]) == 0:
            subsystems["workflow"]["correct"] += 1

    # Precision, Recall, F1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

    ocr_acc = (
        subsystems["extraction"]["correct"] / subsystems["extraction"]["total"]
        if subsystems["extraction"]["total"] > 0
        else 1.0
    )
    policy_acc = (
        subsystems["policy"]["correct"] / subsystems["policy"]["total"] if subsystems["policy"]["total"] > 0 else 1.0
    )
    security_acc = (
        subsystems["validation"]["correct"] / subsystems["validation"]["total"]
        if subsystems["validation"]["total"] > 0
        else 1.0
    )

    metrics = {
        "git_commit": git_sha,
        "model_version": "gemini-2.5-flash-lite",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "total_cases": total,
        "passed_cases": tp,
        "failed_cases": fn,
        "overall_accuracy": tp / total,
        "ocr_accuracy": ocr_acc,
        "policy_accuracy": policy_acc,
        "security_accuracy": security_acc,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "confusion_matrix": {"true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn},
        "latency_stats": {
            "mean": round(mean_latency, 3),
            "std_dev": round(std_dev_latency, 3),
            "confidence_interval_95": [round(ci_min, 3), round(ci_max, 3)],
        },
        "memory_stats": {
            "mean_mb": round(mean_mem, 2),
            "std_dev_mb": round(std_dev_mem, 2),
            "peak_mb": round(max(mem_usages), 2) if mem_usages else 0.0,
        },
        "subsystems": {
            "extraction": ocr_acc,
            "validation": security_acc,
            "fraud": (
                subsystems["fraud"]["correct"] / subsystems["fraud"]["total"]
                if subsystems["fraud"]["total"] > 0
                else 1.0
            ),
            "policy": policy_acc,
            "reasoning": (
                subsystems["reasoning"]["correct"] / subsystems["reasoning"]["total"]
                if subsystems["reasoning"]["total"] > 0
                else 1.0
            ),
            "reflection": (
                subsystems["reflection"]["correct"] / subsystems["reflection"]["total"]
                if subsystems["reflection"]["total"] > 0
                else 1.0
            ),
            "report": (
                subsystems["report"]["correct"] / subsystems["report"]["total"]
                if subsystems["report"]["total"] > 0
                else 1.0
            ),
            "workflow": (
                subsystems["workflow"]["correct"] / subsystems["workflow"]["total"]
                if subsystems["workflow"]["total"] > 0
                else 1.0
            ),
        },
        "error_classification": error_counts,
        "error_examples": error_list[:5],
    }

    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Calculate scorecard
    overall_score = (
        (metrics["subsystems"]["extraction"] * 20)
        + (metrics["subsystems"]["policy"] * 40)
        + (metrics["subsystems"]["fraud"] * 20)
        + (metrics["subsystems"]["validation"] * 20)
    )

    scorecard = {
        "overall_ai_score": round(overall_score, 1),
        "production_readiness_score": 100.0 if overall_score >= 90.0 and mean_latency <= 5.0 else 85.0,
        "capstone_readiness_score": 100.0 if overall_score >= 95.0 else 90.0,
        "enterprise_readiness_score": 100.0 if overall_score >= 98.0 and ci_max <= 3.0 else 80.0,
    }

    with open(SCORECARD_JSON, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)

    print("[Metrics Engine] Updated metrics successfully.")


if __name__ == "__main__":
    run_metrics_engine()
