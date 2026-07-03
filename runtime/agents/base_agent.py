"""runtime/agents/base_agent.py

Defines the abstract base class for agents within the Expense Audit Bot framework.
"""
import abc
from typing import Any, Dict

class BaseAgent(abc.ABC):
    """Abstract base for all agents.

    Subclasses should implement the `process` coroutine which receives a request
    dictionary and returns a response dictionary.
    """
    @abc.abstractmethod
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming request and return a response.
        """
        raise NotImplementedError
