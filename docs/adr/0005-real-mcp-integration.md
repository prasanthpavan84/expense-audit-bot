# ADR 0005: Model Context Protocol (MCP) Integrations

## Status
Approved

## Context
Mocking all external systems (like database files, currencies, or github logs) using fake classes weakens the credibility of a production-grade agent system. We need to implement standard interfaces that leverage real Model Context Protocol (MCP) clients where practical.

## Decision
We leverage the Model Context Protocol (MCP) standard to interface with system tools:
1. **Filesystem MCP**: Directly interacts with absolute paths in the workspace to read/write receipts and logs.
2. **Policy MCP**: Retrieves markdown or json files representing the active company expense compliance standards.
3. **Simulation Separation**: When real MCP integrations are not feasible (e.g. rate-limited live currency converters or sandbox databases), we write a clean, clearly labeled simulation interface and document it for reviewers.

## Consequences
- High architectural alignment with standard Google ADK and MCP patterns.
- Simplified transition from simulated sandbox tools to enterprise production APIs.
