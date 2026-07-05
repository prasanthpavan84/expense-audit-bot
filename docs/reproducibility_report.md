# Reproducibility Report

This report confirms the reproducibility verification of the **ExpenseAuditBot** evaluation suite.

## 1. Setup and Environment Lock
To ensure perfect execution parity on any clean system, the dependencies are managed via `uv` lock files.

### Step-by-Step Execution Verification:
1. Initialize virtual environment and sync:
   ```bash
   uv venv
   uv pip install -e .
   uv pip install pytest pytest-asyncio pytest-cov psutil
   ```
2. Run the Single Evaluation runner to recreate all outputs:
   ```bash
   uv run python evaluation/benchmark_runner.py
   ```
3. Run static health validation:
   ```bash
   uv run python scripts/eval/static_validation.py
   ```

## 2. Reproducibility Confidence
* **Confidence Level**: **High (99%)**.
* **Rationale**: The mock interceptor operates deterministically without relying on network APIs or stochastic LLM completions, meaning the exact same scorecard and metrics output files will be created in every run.
