# Event Bus package placeholder

"""In‑process publish/subscribe event bus.

The real implementation will support async listeners and optional persistence.
For now a minimal synchronous version is provided to allow agents to emit
and listen to events during development.
"""

from collections import defaultdict
from typing import Callable, Dict, List, Any

class EventBus:
    """Simple synchronous event bus.

    Listeners are functions that accept a single payload argument.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Register a handler for a specific ``event_type``.

        Args:
            event_type: Identifier for the type of event (e.g. "receipt_parsed").
            handler: Callable that receives the event payload.
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any) -> None:
        """Publish an event to all registered handlers.

        Handlers are called in the order they were registered.
        """
        for handler in self._subscribers.get(event_type, []):
            handler(payload)
