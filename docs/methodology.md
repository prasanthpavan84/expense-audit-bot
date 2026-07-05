# Evaluation Methodology

This document details the scientific methodology used to evaluate the **ExpenseAuditBot** without modifying production code.

## 1. Pipeline Phases

1. **Benchmark Manifest Discovery**: Discovers all ground-truth cases from `datasets/*.csv` and normalizes them into `benchmark/benchmark_manifest.json`.
2. **Single-Run Execution**: Executes the workflow once per benchmark case, capturing raw text, memory footprints, execution intervals, and state properties.
3. **Statistical Metrics Calculation**: Computes classification precision, recall, confusion matrix values, latency confidence intervals, and fails classifications.
4. **Markdown Report Generation**: Synthesizes structured evaluation records into standalone files under `reports/`.

## 2. Metrics & Formulas

* **OCR Accuracy**:
  $$\text{OCR Accuracy} = \frac{\text{Passed OCR Cases}}{\text{Total OCR Cases}}$$
* **Precision / Recall / F1 Score**:
  $$\text{Precision} = \frac{TP}{TP + FP}$$
  $$\text{Recall} = \frac{TP}{TP + FN}$$
  $$\text{F1} = \frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
* **95% Latency Confidence Interval**:
  $$\mu \pm 1.96 \times \frac{\sigma}{\sqrt{N}}$$

## 3. Sandboxed Offline Mock Testing

To prevent rate limits and avoid dynamic token consumption during regression validation, we leverage a deterministic mock patcher inside `EnterpriseEvaluator` which intercepts `Gemini.generate_content_async` calls and supplies stable mock payloads based on matching prompt identifiers.
