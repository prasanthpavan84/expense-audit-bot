# Reviewer & Interviewer Guide

This guide compiles anticipated questions from technical reviewers and interviewers regarding system design decisions, telemetry, and evaluation metrics.

## 1. System Telemetry & Isolation
* **Isolation Philosophy**: Telemetry and metrics calculation are kept strictly outside of the core application. Dynamic wrapper instrumentation runs during test executions and writes to `evaluation/results.json` without modifying any production imports or lines.
* **Component-Level Evaluation**: Instead of evaluating the bot as a black box, each sub-component (OCR, Policy, Fraud, Security) is scored independently in the weighted scorecard to guarantee granular observability.

## 2. Dynamic Performance Collection
* Process execution statistics (CPU, memory footprints) are captured using the system's `psutil` interface at the start and end of each case, ensuring no overhead or instrumentation files are added to production execution paths.
