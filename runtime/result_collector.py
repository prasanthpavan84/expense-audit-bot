"""runtime/result_collector.py

A very simple in‑process collector to store agent execution results.
It is deliberately lightweight – just a list with helper methods.
"""

from typing import List, Dict

class ResultCollector:
    _results: List[Dict] = []

    @classmethod
    def add(cls, result: Dict) -> None:
        """Append a result dictionary to the internal list."""
        cls._results.append(result)

    @classmethod
    def get_results(cls) -> List[Dict]:
        """Return a shallow copy of all stored results."""
        return list(cls._results)

    @classmethod
    def clear(cls) -> None:
        """Remove all stored results."""
        cls._results.clear()
