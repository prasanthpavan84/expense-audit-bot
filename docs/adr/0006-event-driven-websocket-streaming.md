# ADR 0006: Event-Driven WebSocket Streaming

## Status
Approved

## Context
Exposing agent execution details on the dashboard using REST API polling leads to high database read load, slow UI updates, and an unreactive interface. We need a way to stream events in real-time as they happen.

## Decision
We decouple our workflow engine execution from the API/UI layers using a pub-sub model:
1. **Event Bus**: An in-process pub-sub `EventBus` class notifies registered listeners of execution milestones (e.g. `WorkflowStarted`, `AgentStarted`, `AgentCompleted`, `WorkflowCompleted`).
2. **WebSocket Manager**: A central WebSocket dispatcher `/api/v1/ws/console` listens to these EventBus alerts and broadcasts them immediately to all connected browsers.

## Consequences
- The browser interface receives updates instantly with zero REST polling overhead.
- Frontend rendering of the active Mermaid node and Gantt latencies updates in real-time as the agent runs.
