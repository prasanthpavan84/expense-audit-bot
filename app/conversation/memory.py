from typing import Any, Dict

class SessionMemory:
    """In-memory store for per-session audit context.

    Stores the last expense, decision trace, and any auxiliary data for a given session_id.
    """
    _store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_session(cls, session_id: str) -> Dict[str, Any]:
        if session_id not in cls._store:
            cls._store[session_id] = {
                "session_id": session_id,
                "history": [],
            }
        return cls._store[session_id]

    @classmethod
    def update_session(cls, session_id: str, data: Dict[str, Any]) -> None:
        session = cls.get_session(session_id)
        session.update(data)

    @classmethod
    def add_to_history(cls, session_id: str, item: Any) -> None:
        session = cls.get_session(session_id)
        session["history"].append(item)
