import json
import os
import threading
import time
import uuid
from typing import Any


class SessionMemory:
    """In-memory store for per-session audit context with TTL eviction, persistence, and rolling history.

    Stores the last expense, decision trace, and any auxiliary data for a given session_id.
    """

    _store: dict[str, dict[str, Any]] = {}
    _last_accessed: dict[str, float] = {}
    _ttl_seconds: int = 1800  # 30 minutes
    _max_history_size: int = 1000  # configurable history size
    _lock = threading.RLock()
    _backup_file = os.path.join(os.path.dirname(__file__), ".session_backup.json")

    @classmethod
    def set_ttl(cls, seconds: int) -> None:
        with cls._lock:
            cls._ttl_seconds = seconds

    @classmethod
    def set_max_history_size(cls, size: int) -> None:
        with cls._lock:
            cls._max_history_size = size

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._store.clear()
            cls._last_accessed.clear()
            if os.path.exists(cls._backup_file):
                try:
                    os.remove(cls._backup_file)
                except Exception:
                    pass

    @classmethod
    def _load_backup(cls) -> None:
        with cls._lock:
            if not cls._store and os.path.exists(cls._backup_file):
                try:
                    with open(cls._backup_file, encoding="utf-8") as f:
                        data = json.load(f)
                        cls._store = data.get("store", {})
                        cls._last_accessed = data.get("last_accessed", {})
                except Exception:
                    pass

    @classmethod
    def _save_backup(cls) -> None:
        with cls._lock:
            try:
                serialized_store = {}
                for sid, data in cls._store.items():
                    serializable_history = []
                    for item in data.get("history", []):
                        try:
                            json.dumps(item)
                            serializable_history.append(item)
                        except (TypeError, OverflowError):
                            serializable_history.append(str(item))
                    
                    session_copy = dict(data)
                    session_copy["history"] = serializable_history
                    serialized_store[sid] = session_copy

                with open(cls._backup_file, "w", encoding="utf-8") as f:
                    json.dump({"store": serialized_store, "last_accessed": cls._last_accessed}, f, indent=2)
            except Exception:
                pass

    @classmethod
    def _cleanup_stale_sessions(cls) -> None:
        with cls._lock:
            now = time.time()
            stale_keys = [sid for sid, last_time in cls._last_accessed.items() if now - last_time > cls._ttl_seconds]
            if stale_keys:
                for sid in stale_keys:
                    cls._store.pop(sid, None)
                    cls._last_accessed.pop(sid, None)
                cls._save_backup()

    @classmethod
    def get_session(cls, session_id: str) -> dict[str, Any]:
        with cls._lock:
            cls._load_backup()
            cls._cleanup_stale_sessions()
            if not session_id or session_id == "default-session":
                session_id = "session-default"
            cls._last_accessed[session_id] = time.time()
            if session_id not in cls._store:
                cls._store[session_id] = {
                    "session_id": session_id,
                    "history": [],
                    "metadata": {}
                }
            return cls._store[session_id]

    @classmethod
    def update_session(cls, session_id: str, data: dict[str, Any]) -> None:
        with cls._lock:
            session = cls.get_session(session_id)
            for k, v in data.items():
                if k == "history" and isinstance(v, list):
                    session["history"] = v[-cls._max_history_size:]
                else:
                    session[k] = v
            cls._last_accessed[session_id] = time.time()
            cls._save_backup()

    @classmethod
    def add_to_history(cls, session_id: str, item: Any) -> None:
        with cls._lock:
            session = cls.get_session(session_id)
            session["history"].append(item)
            if len(session["history"]) > cls._max_history_size:
                session["history"] = session["history"][-cls._max_history_size:]
            cls._last_accessed[session_id] = time.time()
            cls._save_backup()

    @classmethod
    def clear_session(cls, session_id: str) -> None:
        with cls._lock:
            cls._store.pop(session_id, None)
            cls._last_accessed.pop(session_id, None)
            cls._save_backup()
