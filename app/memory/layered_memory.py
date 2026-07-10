import time
from typing import Any

from app.repositories.audit_repository import AuditRepository


class WorkingMemory:
    """Manages the in-flight context state for a single audit execution pipeline."""

    def __init__(self):
        self.variables: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def clear(self):
        self.variables.clear()


class ConversationMemory:
    """Manages conversational history/threads of interactive user queries."""

    def __init__(self):
        self.history: list[dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self.history.append(
            {"role": role, "content": content, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        )

    def get_history(self) -> list[dict[str, str]]:
        return list(self.history)


class ToolMemory:
    """Cache for expensive tool/MCP operations like currency rate lookups."""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache: dict[str, dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        entry = self.cache.get(key)
        if entry:
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["value"]
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self.cache[key] = {"value": value, "timestamp": time.time()}


class LayeredMemory:
    """Facade exposing all structured memory tiers."""

    def __init__(self, audit_repo: AuditRepository | None = None):
        self.working = WorkingMemory()
        self.conversation = ConversationMemory()
        self.tool = ToolMemory()
        self.audit = audit_repo or AuditRepository()


# Expose global memory manager
layered_memory = LayeredMemory()
