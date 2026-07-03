# core/event_bus/message_bus.py
"""A simple synchronous in‑process message bus.

The design mirrors a lightweight event system suitable for the initial
prototype.  It supports subscription of callables and publishing of a
payload.  Future iterations can replace this with an async or persistent
implementation (e.g., Redis, RabbitMQ) without changing the consuming
agents.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List


class MessageBus:
    """Synchronous publish‑subscribe message bus.

    Listeners register via :meth:`subscribe` and are invoked in the order
    they were added when :meth:`publish` is called.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Register a ``handler`` for ``event_type``.

        Args:
            event_type: A string identifier for the event (e.g., ``"receipt_parsed"``).
            handler: Callable that accepts a single payload argument.
        """

        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any) -> None:
        """Publish ``payload`` to all handlers registered for ``event_type``.

        Handlers are called synchronously; any exception propagates to the
        caller, which mirrors a simple in‑process event system.
        """

        for handler in self._subscribers.get(event_type, []):
            handler(payload)

    def clear(self) -> None:
        """Remove all subscriber registrations. Useful for test isolation."""

        self._subscribers.clear()

__all__ = ["MessageBus"]
