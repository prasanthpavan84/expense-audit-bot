# Dataset Summary & Ground Truth Catalog

This document details the catalog of ground-truth test data utilized by the evaluation framework.

## 1. Dataset Classifications
The benchmark is constructed from the following files in the `datasets/` directory:

| Dataset File | Evaluation Focus | Number of Cases | Target Metric Goals | Priority |
|---|---|---|---|---|
| `adversarial.csv` | Adversarial prompts, malformed strings | 5 | Security/Sanitization | High |
| `compliance.csv` | Corporate policy and caps | 15 | Policy Engine Accuracy | High |
| `extraction.csv` | Legibility and OCR fields | 20 | OCR Extraction Accuracy | High |
| `robustness.csv` | Spelling typos and variations | 10 | Receipt Understanding | Medium |
| `security.csv` | PII leaks and injections | 10 | Security Pass Rate | High |
| `stress_testing.csv` | High-frequency stress triggers | 6 | Stability & Latency | Medium |

## 2. Manifest Catalog Mapping
Every case is mapped to `benchmark/benchmark_manifest.json` with fields:
* `test_id`: Traced test case ID.
* `input`: Input prompt sequence.
* `expected_result`: Target parsed fields and compliance values.
