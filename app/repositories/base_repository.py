from abc import ABC, abstractmethod
from typing import Any, List, Optional

class BaseRepository(ABC):
    """Abstract base repository contract."""

    @abstractmethod
    def save(self, entity: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        raise NotImplementedError
