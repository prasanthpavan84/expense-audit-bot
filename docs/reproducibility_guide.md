# Reproducibility Guide

This guide ensures that all evaluation scores, performance reports, and static validations are fully reproducible from a clean clone of the repository.

## 1. Quick Setup
Verify your python environment is clean, then run:
```bash
uv venv
uv pip install -e .
uv pip install pytest pytest-asyncio pytest-cov psutil
```

## 2. Execute Benchmark Pipeline
Run the single pipeline to regenerate all results, metrics, and reports:
```bash
uv run python evaluation/benchmark_runner.py
```

## 3. Verify System Health and Immutability
To verify that no circular imports exist and that all frozen production code directories have zero modifications:
```bash
uv run python scripts/eval/static_validation.py
```
This script returns exit code `0` if the codebase is perfectly compliant.
