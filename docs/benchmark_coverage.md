# Benchmark Coverage & Category Distribution

This document outlines the distribution of evaluation cases across system categories.

## 1. Category Distribution
The benchmark manifest is comprised of **66 test cases** distributed across the following domains:

| Category | Cases Count | Primary Subsystem Tested | Evaluation Rule Focus |
|---|---|---|---|
| **OCR Extraction** | 20 | Receipt Extractor | Matching merchant, date, amount, currency |
| **Business Policy** | 15 | Policy Engine | Threshold caps and restricted categories |
| **Security/Injections** | 15 | Security Checkpoint | Blocking PII, adversarial keywords, injection patterns |
| **Robustness & Edge Cases** | 10 | Receipt Extractor / Parser | Spelled variants, spelling errors, negative values |
| **Stress Testing** | 6 | Orchestrator / State | Consecutive execution, latency threshold bounds |

## 2. Manifest Schema Traceability
All 66 cases trace directly to:
* Ground-truth CSV files located in `datasets/`
* `benchmark/benchmark_manifest.json`
* Single execution records in `evaluation/results.json`
