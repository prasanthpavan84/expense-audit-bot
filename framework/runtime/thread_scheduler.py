# framework/runtime/thread_scheduler.py
"""A very simple thread‑based scheduler stub.

The scheduler implements :class:`SchedulerInterface` but does not actually
schedule background jobs – it merely provides ``start`` and ``stop`` methods
so the :class:`RuntimeEngine` can call them without error.  This is sufficient
for the current prototype and can be swapped out for a richer implementation
(e.g., ``AsyncScheduler``) later.
"""

from __future__ import annotations

import threading
from typing import Any

from .interfaces import SchedulerInterface


class ThreadScheduler(SchedulerInterface):
    """No‑op scheduler that runs jobs in the current thread.

    The ``schedule`` method stores the callable and arguments but executes them
    immediately.  This keeps the runtime synchronous, which is ideal for unit
    tests and the initial demo.
    """

    def __init__(self) -> None:
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Mark the scheduler as running. No background thread is started."""
        with self._lock:
            self._running = True
        # In a full implementation we would spin up a worker thread here.

    def stop(self) -> None:
        """Mark the scheduler as stopped."""
        with self._lock:
            self._running = False

    def schedule(self, *args: Any, **kwargs: Any) -> None:
        """Execute the supplied callable immediately.

        The first positional argument is expected to be a callable.  Any further
        ``*args``/``**kwargs`` are passed to that callable.
        """
        if not self._running:
            raise RuntimeError("ThreadScheduler is not started")
        if not args:
            raise ValueError("No callable provided to schedule")
        func = args[0]
        func_args = args[1:]
        func_kwargs = kwargs
        # Synchronous execution – suitable for the prototype.
        func(*func_args, **func_kwargs)

__all__ = ["ThreadScheduler"]
