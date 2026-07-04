# ADR 0004: Capability-Based Tool Registry

## Status
Approved

## Context
Tying agents directly to specific tool classes (e.g. importing `FilesystemTool` inside `ReceiptAgent`) makes it impossible to switch tool providers (e.g., using local filesystem tool during development and migrating to S3 or SAP tool in production) without changing agent logic.

## Decision
We decouple tool usage from tool implementation using a **Capability-Based Tool Registry**:
1. Agents request abstract capabilities (e.g. `FILE_READ`, `CONVERT_CURRENCY`, `READ_POLICY`) rather than specific instances.
2. The `ToolRegistry` maps these capabilities to their active providers (e.g. Filesystem MCP, Currency API).
3. Agents invoke tools dynamically using the resolved provider handlers.

## Consequences
- Clean separation between tool definitions and actual MCP implementations.
- Tool providers can be dynamically toggled or replaced in configuration YAMLs with zero impact on agent code.
