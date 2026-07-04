from typing import Dict, Any, List, Optional
import time
from app.repositories.audit_repository import AuditRepository

class WorkingMemory:
    """Manages the in-flight context state for a single audit execution pipeline."""

    def __init__(self):
        self.variables: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def clear(self):
        self.variables.clear()


class ConversationMemory:
    """Manages conversational history/threads of interactive user queries."""

    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

    def get_history(self) -> List[Dict[str, str]]:
        return list(self.history)


class ToolMemory:
    """Cache for expensive tool/MCP operations like currency rate lookups."""

    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if entry:
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["value"]
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self.cache[key] = {
            "value": value,
            "timestamp": time.time()
        }


class LayeredMemory:
    """Facade exposing all structured memory tiers."""

    def __init__(self, audit_repo: Optional[AuditRepository] = None):
        self.working = WorkingMemory()
        self.conversation = ConversationMemory()
        self.tool = ToolMemory()
        self.audit = audit_repo or AuditRepository()

# Expose global memory manager
layered_memory = LayeredMemory()
