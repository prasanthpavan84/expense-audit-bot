# Benchmark Guide

This document describes how to execute the benchmark suite and analyze the results.

## 1. Running the Benchmarks
To run the Single Evaluation Pipeline benchmark:
```bash
uv run python evaluation/benchmark_runner.py
```
This script will:
1. Parse the CSV files to generate `benchmark/benchmark_manifest.json`.
2. Run each benchmark case exactly once.
3. Save the results into `evaluation/results.json`.
4. Run `evaluation/metrics.py` to calculate statistical metrics in `evaluation/metrics.json`.
5. Generate the 12 markdown reports under `reports/`.

## 2. Directory Layout
* `benchmark/benchmark_manifest.json`: Single source of truth defining all test cases.
* `evaluation/results.json`: Execution outcomes, raw output, latencies, and memory footprints.
* `evaluation/metrics.json`: Statistical metrics (precision, recall, confidence intervals, error counts).
* `evaluation/scorecard.json`: Readiness and overall AI scorecards.
* `reports/`: Folder containing all 12 Markdown performance reports.
