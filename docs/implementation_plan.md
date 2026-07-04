# Expense Audit Bot

## Master Implementation Roadmap

### Project Goal
Create a production‑grade expense‑audit AI system that ingests receipts, validates data, detects fraud, applies corporate policies, and generates explainable reports. The system will be architected for clean separation of concerns, thorough testing, rich evaluation, and easy deployment.

### Project Architecture
- **Core Runtime** – `RuntimeEngine`, `RuntimeContext`, `WorkflowContext`, `StateManager`, `EventBus`, `Scheduler`, `SharedMemory`, `ArtifactManager`, `Registry`.
- **AI Runtime** – `Planner`, `WorkflowExecutor`, `AgentExecutor`, `BaseAgent` lifecycle, LLM abstraction, Security, Validation.
- **Business Logic** – OCR, Receipt Analysis, Validation, Fraud Detection, Policy Engine, Reflection, Report generation, Explainability.
- **Evaluation** – Metrics, AI Health, Decision Trace/Graph, Scorecards, Benchmark Runner, Experiment Tracking.
- **User Experience** – FastAPI API, Streamlit dashboard, workflow replay, analytics, explainability, reports.
- **Production Readiness** – Docker, GitHub Actions, comprehensive test suite, documentation, model card, ADRs, demo script.

---

## Milestones

### Milestone 1 – Core Runtime
**Status:** ✅ Completed
- `RuntimeEngine`
- `RuntimeContext`
- `WorkflowContext`
- `StateManager` (12‑state FSM)
- `EventBus`
- `ThreadScheduler`
- `SharedMemory` (typed memories)
- `ArtifactManager`
- `Registries` (agents, workflows, models)

### Milestone 2 – AI Runtime
**Status:** 🟡 In Progress
- `Planner` (Intent → Workflow → ExecutionPlan)
- `WorkflowExecutor`
- `AgentExecutor`
- `BaseAgent` lifecycle hooks
- LLM abstraction (`BaseProvider`, `GeminiProvider`, `MockProvider`)
- Security layer (`ExecutionGuard`, `CognitiveFirewall`)
- Validation utilities

### Milestone 3 – Business Agents
**Status:** ⬜ Not Started
- OCR Agent
- Receipt Analysis Agent
- Validation Agent
- Fraud Detection Agent
- Policy Agent
- Reflection Agent
- Report Agent
- Explainability Engine (per‑step reasoning)

### Milestone 4 – Evaluation Engine
**Status:** ⬜ Not Started
- Metrics collector (execution time, retries, token usage, memory)
- AI Health scoring (confidence calibration, hallucination detection)
- Decision trace & graph generation
- Scorecards (accuracy, latency, reliability)
- Benchmark runner (runs curated 500+ receipt dataset)
- Experiment tracking (CSV log of runs, versions, winners)

### Milestone 5 – Dashboard & UX
**Status:** ⬜ Not Started
- FastAPI endpoints (`/run`, `/evaluate`, `/benchmark`, `/metrics`, `/docs`)
- Streamlit dashboard showing:
  - AI Health summary
  - Timeline (Gantt‑style)
  - Decision graph
  - Confidence & fraud scores
  - Agent performance metrics
  - Error distribution analysis
  - Production readiness scorecard
- Decision replay UI (step‑through a past run)
- Exportable reports (HTML, PDF, JSON, Markdown)

### Milestone 6 – Production Readiness
**Status:** ⬜ Not Started
- Dockerfile (multi‑stage, slim image)
- Docker‑compose for FastAPI + Streamlit
- Makefile (build, run, test, lint, deploy)
- GitHub Actions CI/CD (lint, type‑check, unit/integration tests, Docker build)
- Full unit test suite (≥ 90 % coverage) and integration tests
- Security tests (token validation, prompt sanitisation)
- Documentation package (README, ADRs, architecture diagrams, system sequence diagram, component diagram, deployment diagram, model card)
- Demo script (`python demo.py`) that runs a sample receipt, produces a report, opens the dashboard, and prints AI health.

---

## Future Improvements
- Async scheduler stub (`AsyncScheduler`).
- Additional LLM providers (OpenAI, Anthropic).
- Persistent memory back‑ends (SQLite/Redis).
- Advanced event‑bus features (priority queues, replay persistence).
- Full CI pipeline with performance benchmarking.

---

## Change Log / Version History
| Version | Date | Changes |
|---|---|---|
| 0.1.0 | 2026‑07‑03 | Created master roadmap document. |
| 0.1.1 | TBD | Updated milestone statuses after core runtime completion. |

---

## Development Log (placeholder)
See `docs/development_log.md` for day‑by‑day progress entries.
