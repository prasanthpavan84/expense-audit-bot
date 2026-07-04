# ADR 0007: Resilient Checkpoint Recovery

## Status
Approved

## Context
If a long-running multi-agent workflow gets interrupted halfway (due to LLM rate-limiting, internet outages, or API crashes), the system must not restart from the beginning, which would waste execution tokens and double latency.

## Decision
We implement a robust SQLite-based checkpointing mechanism:
1. After every successful agent execution step (e.g. `ReceiptAgent` completes, `FraudAgent` completes), the `WorkflowEngine` serializes the current `WorkflowContext` to the database using `CheckpointRepository`.
2. On triggering a workflow run, the engine checks for active checkpoints for the given `audit_id`.
3. If a checkpoint exists, it restores the state and slices the execution list to resume execution from the failed agent step onwards.

## Consequences
- Guaranteed state recovery in the event of hardware or API crashes.
- Significant savings on input token counts and LLM provider costs during task retries.
