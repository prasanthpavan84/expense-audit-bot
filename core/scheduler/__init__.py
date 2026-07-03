# core/scheduler/__init__.py
"""Thread‑based scheduler implementation for the runtime engine.

This provides a minimal concrete ``SchedulerInterface`` that executes jobs
synchronously in the current thread. It satisfies the runtime's need for a
scheduler without the complexity of async queues (Celery, Redis, etc.).
"""

from __future__ import annotations

from typing import Any, Callable

from ...framework.runtime.interfaces import SchedulerInterface


class ThreadScheduler(SchedulerInterface):
    """Simple synchronous scheduler.

    The ``schedule`` method executes the given callable immediately. ``start``
    and ``stop`` are retained for API compatibility but are essentially no‑ops.
    """

    def __init__(self) -> None:
        self._started = False
        self._jobs: list[Callable[..., Any]] = []

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False
        self._jobs.clear()

    def schedule(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if not self._started:
            self.start()
        self._jobs.append(lambda: func(*args, **kwargs))
        func(*args, **kwargs)
