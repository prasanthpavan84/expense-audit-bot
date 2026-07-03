# framework/runtime/runtime_context.py
"""Data class that carries the immutable and mutable information required
throughout a runtime execution.

The :class:`RuntimeEngine` creates a single instance at start‑up and passes
it to components that need access to shared execution data.  It deliberately
does **not** act as a service locator – components should receive the
specific objects they require via dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuntimeContext:
    """Container for execution‑wide data.

    Attributes
    ----------
    run_id: str
        Unique identifier for this run (e.g., ``run_001``).
    session_id: str
        Identifier for the user session.
    user_id: str
        The user who triggered the workflow.
    workflow: str
        Name or identifier of the workflow being executed.
    execution_token: str
        Security token or opaque identifier for the execution.
    memory: Any
        Reference to the shared ``SharedMemory`` instance.
    services: Any
        Reference to the ``ServiceContainer`` providing injected services.
    metrics: Dict[str, Any]
        Collected runtime metrics (populated by the engine).
    state: Dict[str, Any]
        Arbitrary mutable state that agents can read/write.
    """

    run_id: str
    session_id: str
    user_id: str
    workflow: str
    execution_token: str
    memory: Any
    services: Any
    metrics: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)

    def update_metric(self, key: str, value: Any) -> None:
        """Convenience helper to update a metric in ``metrics``.
        """

        self.metrics[key] = value

    def set_state(self, key: str, value: Any) -> None:
        """Store an arbitrary piece of state.
        """

        self.state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Retrieve a piece of state.
        """

        return self.state.get(key, default)

__all__ = ["RuntimeContext"]
