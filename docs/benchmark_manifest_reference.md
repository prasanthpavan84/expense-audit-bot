# Benchmark Manifest Reference

This document describes the schema structure of `benchmark/benchmark_manifest.json`.

## 1. Case Properties
Each case inside the manifest list contains:
* `test_id`: A unique string identifying the test case.
* `category`: The test domain (e.g. OCR, compliance, security, edge cases).
* `input`: The prompt string passed to the orchestrator.
* `expected_result`: Target properties (expected merchant, amount, compliant decision).
* `ground_truth`: The raw source data dictionary from the CSV dataset.
* `evaluation_rules`: Target validations to apply during testing.
* `priority`: Priority scale (e.g. High, Medium).
* `reusable`: Boolean indicating if the case can be run in regression suites.
