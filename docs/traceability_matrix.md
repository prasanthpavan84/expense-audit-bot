# Traceability Matrix

This matrix traces all major business rules, quality targets, and documentation claims to their corresponding source code, benchmark IDs, and evaluation test cases.

| Claims / Quality Targets | Benchmark ID | Source Code / Public API | Automated Test Code | Evaluation Report |
|---|---|---|---|---|
| **OCR Legibility parsing** | `case_001` - `case_010` | `app/agents/receipt_extractor.py` | `tests/unit/test_receipt_intelligence.py` | `reports/ocr_report.md` |
| **Meals Limits ($100 cap)** | `case_011` - `case_020` | `app/business_rules/policy_engine.py` | `tests/unit/test_policy.py` | `reports/policy_report.md` |
| **Restricted Vendor Fraud** | `case_021` - `case_030` | `app/agents/fraud_detector.py` | `tests/unit/test_fraud.py` | `reports/fraud_report.md` |
| **Prompt Injection Protection** | `sec1`, `sec2` | `app/agent.py` (security checkpoint) | `tests/edge_cases/test_edge_cases.py` | `reports/security_report.md` |
| **Intent Routing (Audit/Query)** | `case_031` - `case_040` | `app/agent.py` (intent router) | `tests/unit/test_queries.py` | `reports/benchmark_report.md` |
| **Stress Testing Stability** | `str1`, `str2` | `app/agent.py` | `tests/edge_cases/test_edge_cases.py` | `reports/stress_report.md` |
| **SLA Latency limits** | All cases | `evaluation/benchmark_runner.py` | `tests/edge_cases/test_edge_cases.py` | `reports/performance_report.md` |
