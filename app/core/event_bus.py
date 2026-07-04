from typing import Dict, List, Callable, Any

class EventBus:
    """Lightweight in-process Event Bus implementing Pub-Sub pattern."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
        return cls._instance

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Register a handler callback for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any) -> None:
        """Dispatch event payload to all registered handlers for the type."""
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception:
                # Silently catch handler exceptions to prevent blocking publisher
                pass

# Global Event Bus instance
event_bus = EventBus()
