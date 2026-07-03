# framework/runtime/interfaces.py
"""Abstract interfaces for components used by the runtime engine.

These allow the engine to be instantiated with test doubles or real
implementations without changing its code.
"""

from __future__ import annotations

import abc
from typing import Any


class SchedulerInterface(abc.ABC):
    """Interface for a task scheduler.

    The concrete implementation may schedule background tasks, recurring
    jobs, or one‑off timers.
    """

    @abc.abstractmethod
    def start(self) -> None:
        """Start the scheduler and begin processing scheduled jobs."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the scheduler and cancel any pending jobs."""

    @abc.abstractmethod
    def schedule(self, *args: Any, **kwargs: Any) -> None:
        """Schedule a new job. The signature is left generic for flexibility."""


class PlannerInterface(abc.ABC):
    """Interface for a workflow planner that prepares execution plans."""

    @abc.abstractmethod
    def initialize(self) -> None:
        """Prepare internal structures before any workflow runs."""

    @abc.abstractmethod
    def plan(self, workflow_name: str, context: Any) -> Any:
        """Generate a plan for ``workflow_name`` given the current ``context``.

        Returns an opaque plan object that the executor will later consume.
        """


class ArtifactManagerInterface(abc.ABC):
    """Interface for persisting runtime artifacts such as logs and JSON traces."""

    @abc.abstractmethod
    def create_execution_bundle(self, run_id: str) -> str:
        """Create a directory for a new execution and return its path.

        The directory should contain the standard JSON files listed in the
        design (workflow.json, timeline.json, etc.).
        """

    @abc.abstractmethod
    def write_artifact(self, path: str, filename: str, data: Any) -> None:
        """Write ``data`` to ``filename`` inside ``path``.

        ``data`` is usually a serialisable Python object (dict, list, etc.).
        """

__all__ = ["SchedulerInterface", "PlannerInterface", "ArtifactManagerInterface"]
