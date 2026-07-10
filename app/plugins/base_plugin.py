from abc import ABC, abstractmethod
from typing import Any


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
    def check(
        self, expense: dict[str, Any], history: list[dict[str, Any]] = None, session_items: list[dict[str, Any]] = None
    ) -> tuple[int, str]:
        """Runs the plugin fraud check logic.

        Returns:
            Tuple: (risk_score_contribution, reason_string)
        """
        raise NotImplementedError
