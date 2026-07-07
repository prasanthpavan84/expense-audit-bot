"""
Event Bus for Expense Audit Bot

Provides a simple publish-subscribe mechanism for internal events.
"""

from collections import defaultdict
from collections.abc import Callable
from typing import Any


class EventBus:
    """Simple in-process event bus."""

    def __init__(self) -> None:
        self._subscribers: defaultdict[str, list[Callable[[Any], None]]] = defaultdict(
            list
        )

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any) -> None:
        for handler in self._subscribers.get(event_type, []):
            handler(payload)
