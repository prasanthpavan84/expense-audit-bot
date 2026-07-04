from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple

class BasePlugin(ABC):
    """Abstract base class for all fraud plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def author(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def priority(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def check(self, expense: Dict[str, Any], history: List[Dict[str, Any]] = None, session_items: List[Dict[str, Any]] = None) -> Tuple[int, str]:
        """Runs the plugin fraud check logic.

        Returns:
            Tuple: (risk_score_contribution, reason_string)
        """
        raise NotImplementedError
