# ADR 0003: Dynamic YAML-Based Workflow Engine

## Status
Approved

## Context
Orchestrating agents in a hardcoded pipeline (e.g. `Parser` -> `Validator` -> `Fraud` -> `Policy` -> `Decision`) requires modifying Python files whenever a step is added, re-ordered, or skipped. This violates the Open-Closed Principle and hinders maintainability.

## Decision
We implement a dynamic `WorkflowEngine` that:
1. Loads execution sequences from a YAML file (`expense_workflow.yaml`).
2. Uses a `WorkflowValidator` to parse the YAML, perform cycle detection (preventing infinite loops), and validate connectivity.
3. Automatically resolves and executes the sequential list of agents via the `AgentRegistry`.

## Consequences
- Adding or changing workflows is done entirely by editing the YAML configuration file, requiring zero modifications to Python code.
- Mermaid visualizers can read this YAML structure directly to render workflow paths dynamically on the dashboard.
