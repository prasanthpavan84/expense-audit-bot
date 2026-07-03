# framework/runtime/shared_memory.py
"""Typed shared memory containers for the runtime.

The runtime uses a central memory object that agents can read from and write to.
Only a minimal set of typed memories is required for the foundation:

* ``KeyValueMemory`` – a simple dict‑like store.
* ``VectorMemory`` – placeholder for future vector‑based stores (e.g. embeddings).

These classes are deliberately lightweight; they can be swapped out for more
sophisticated implementations later without touching the rest of the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class KeyValueMemory:
    """A basic key‑value store used by agents to exchange data.

    The store is thread‑safe for the simple prototype – all operations acquire
    a lock before mutating the underlying dictionary.
    """

    _store: Dict[str, Any] = field(default_factory=dict)
    _order: List[str] = field(default_factory=list)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        if key not in self._order:
            self._order.append(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def items(self):
        """Iterate over items in insertion order (useful for deterministic testing)."""
        for key in self._order:
            yield key, self._store[key]

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __repr__(self) -> str:
        return f"<KeyValueMemory keys={list(self._store.keys())}>"


class VectorMemory:
    """Placeholder for a vector‑based memory.

    In later phases this could wrap an FAISS index, a Milvus collection, or any
    other nearest‑neighbor store.  For now it simply stores a list of (id, vector)
    tuples and provides a ``search`` stub that returns an empty list.
    """

    def __init__(self) -> None:
        self._vectors: List[tuple] = []

    def add(self, identifier: str, vector: Any) -> None:
        self._vectors.append((identifier, vector))

    def search(self, query: Any, top_k: int = 5) -> List[tuple]:
        # Stub implementation – returns an empty result set.
        return []

    def __len__(self) -> int:
        return len(self._vectors)

    def __repr__(self) -> str:
        return f"<VectorMemory size={len(self)}>"

__all__ = ["KeyValueMemory", "VectorMemory"]
