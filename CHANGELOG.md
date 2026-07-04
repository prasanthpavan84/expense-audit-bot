# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-07-04
### Added
- **Enterprise Operations Console**: Multi-tab SPA console under `/dashboard` featuring system diagnostics, agent drawer inspector, dynamic Gantt latencies, and preloaded capstone demo scenarios.
- **WebSocket Streaming Event Hub**: Live broadcasts from the in-process EventBus to dashboard websocket subscribers.
- **Correlation ID Middleware**: Auto-injection of trace headers (`X-Correlation-ID`) across requests and logs.
- **Structured Exception Handlers**: Consistent global JSON error mapping.
- **Changelog, Contributing, and Code of Conduct**: Complete production documentation.

### Fixed
- Fixed Gemini API calls hanging in offline sandboxes by introducing lazy index building in RAG service.
- Fixed typing and interface imports across all core agents.
- Synchronized reflection contradiction outputs in the `process_state` flow.
