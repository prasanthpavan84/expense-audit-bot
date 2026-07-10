import json
import os
import time


class ReportGenerator:
    @staticmethod
    def generate_json_results(results: dict, output_path: str):
        """Saves evaluation metrics to a structured JSON file."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"JSON results saved to: {output_path}")

    @staticmethod
    def generate_markdown_report(metrics: dict, output_path: str):
        """Saves a detailed evaluation report to a Markdown file."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        report = f"""# AI Agent Evaluation Report
Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

This report summarizes the performance and accuracy of the **ExpenseAuditBot** across all evaluation datasets.

## 1. Executive Summary

- **Overall Decision Accuracy**: **{metrics.get('overall_accuracy', 0.0):.2%}**
- **Average Execution Latency**: **{metrics.get('avg_latency', 0.0)} s**
- **P95 Latency**: **{metrics.get('p95_latency', 0.0)} s**
- **Success Rate**: **{metrics.get('success_rate', 0.0):.2%}**
- **Failure Rate**: **{metrics.get('failure_rate', 0.0):.2%}**

## 2. Component Accuracy Metrics

| Component | Evaluated Metric | Accuracy |
| :--- | :--- | :--- |
| **OCR Extraction** | OCR Exact Match Accuracy | {metrics.get('ocr_accuracy', 0.0):.2%} |
| **Policy Enforcement** | Policy Detection Accuracy | {metrics.get('policy_accuracy', 0.0):.2%} |
| **Fraud Detection** | Fraud Detection Accuracy | {metrics.get('fraud_accuracy', 0.0):.2%} |
| **Orchestrator** | Overall Graph Decision Parity | {metrics.get('overall_accuracy', 0.0):.2%} |

## 3. Dataset Summary

- **Total Cases Executed**: {metrics.get('total_cases', 0)}
- **Passed Cases**: {metrics.get('passed_cases', 0)}
- **Failed Cases**: {metrics.get('failed_cases', 0)}

---
*Report generated automatically by the Benchmark Suite.*
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Markdown report written to: {output_path}")

    @staticmethod
    def generate_benchmark_comparison(legacy_metrics: dict, agent_metrics: dict, output_path: str):
        """Generates a comparison markdown report between the Baseline Rule Engine and Multi-Agent Workflow."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        report = f"""# Benchmark Comparison: Baseline vs Multi-Agent Workflow
Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

This report compares a traditional, regex-based **Baseline Rule Engine** against the **Current Multi-Agent Workflow**.

## 1. Key Performance Indicators (KPIs)

| Dimension | Baseline Rule Engine | Current Multi-Agent Workflow | Improvement |
| :--- | :---: | :---: | :---: |
| **OCR Accuracy** | {legacy_metrics.get('ocr_accuracy', 0.0):.2%} | {agent_metrics.get('ocr_accuracy', 0.0):.2%} | **+{agent_metrics.get('ocr_accuracy', 0.0) - legacy_metrics.get('ocr_accuracy', 0.0):.2%}** |
| **Policy Accuracy** | {legacy_metrics.get('policy_accuracy', 0.0):.2%} | {agent_metrics.get('policy_accuracy', 0.0):.2%} | **+{agent_metrics.get('policy_accuracy', 0.0) - legacy_metrics.get('policy_accuracy', 0.0):.2%}** |
| **Fraud Accuracy** | {legacy_metrics.get('fraud_accuracy', 0.0):.2%} | {agent_metrics.get('fraud_accuracy', 0.0):.2%} | **+{agent_metrics.get('fraud_accuracy', 0.0) - legacy_metrics.get('fraud_accuracy', 0.0):.2%}** |
| **Overall Decision Accuracy** | {legacy_metrics.get('overall_accuracy', 0.0):.2%} | {agent_metrics.get('overall_accuracy', 0.0):.2%} | **+{agent_metrics.get('overall_accuracy', 0.0) - legacy_metrics.get('overall_accuracy', 0.0):.2%}** |
| **Average Latency** | {legacy_metrics.get('avg_latency', 0.0)} s | {agent_metrics.get('avg_latency', 0.0)} s | {round(legacy_metrics.get('avg_latency', 0.0) - agent_metrics.get('avg_latency', 0.0), 3)} s |
| **Failure Rate** | {legacy_metrics.get('failure_rate', 0.0):.2%} | {agent_metrics.get('failure_rate', 0.0):.2%} | {round(legacy_metrics.get('failure_rate', 0.0) - agent_metrics.get('failure_rate', 0.0), 4):.2%} |

## 2. Qualitative Assessment

### Baseline Rule Engine
* **Strengths**: Low latency, deterministic execution, and zero token costs.
* **Weaknesses**: Extremely fragile to formatting variations, unable to handle currency conversions dynamically, cannot detect semantic fraud, and fails on adversarial prompt inputs.

### Current Multi-Agent Workflow
* **Strengths**: Robust entity extraction under blurry/noisy OCR conditions, context-aware policy enforcement, deep fraud intelligence reasoning, and dynamic exception handling.
* **Weaknesses**: Slightly higher execution latency due to model inference cycles and token consumption costs.
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Benchmark comparison written to: {output_path}")
