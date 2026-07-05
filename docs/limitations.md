# Limitations & Future Extensions

This document outlines the limitations of the evaluation framework and proposes future remediations.

## 1. Sandbox Mocking Limitations
* **Stochastic Variance**: The evaluation pipeline uses deterministic mock responses. It does not measure live LLM hallucinations, prompt drift, or rate limit throttling under actual Gemini API usage.
* **Ground-Truth Mismatch**: If an input is supplied that does not match one of the predefined mock receipt categories, the system defaults to validation fallback.

## 2. Telemetry and Resource Overhead
* **Memory Tracking**: Process memory statistics are tracked via `psutil`. This measures total process RSS growth, which includes general Python overhead and import caches, not just the isolated memory footprint of the graph execution.
* **Token Tracking**: Token usage is simulated using average limits because the mock LLM does not return actual API token billing headers.
