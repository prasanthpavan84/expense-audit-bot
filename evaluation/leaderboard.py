"""evaluation/leaderboard.py

In‑memory leaderboard that keeps top‑N scorecards based on a numeric score.

The leaderboard can be queried to retrieve the current ranking.
"""


class Leaderboard:
    def __init__(self, max_entries: int = 10) -> None:
        self.max_entries = max_entries
        # Store entries as (score, scorecard_str)
        self.entries: list[tuple[float, str]] = []

    def add_entry(self, score: float, scorecard: str) -> None:
        """Add a new entry and keep only top ``max_entries``.

        Entries are sorted descending by ``score``.
        """
        self.entries.append((score, scorecard))
        self.entries.sort(key=lambda x: x[0], reverse=True)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[: self.max_entries]

    def get_top(self) -> list[tuple[float, str]]:
        """Return a list of (score, scorecard) tuples in ranking order."""
        return self.entries
