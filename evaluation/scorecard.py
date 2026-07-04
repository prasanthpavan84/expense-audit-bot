"""evaluation/scorecard.py

Defines a simple Scorecard that aggregates evaluation results.
"""

class Scorecard:
    """Collects metric results and provides summary utilities."""
    def __init__(self):
        self.scores = {}

    def add_score(self, metric_name: str, value):
        self.scores[metric_name] = value

    def overall(self):
        """Return an overall summary. For now just an average of numeric scores.
        Non‑numeric entries are ignored.
        """
        numeric = [v for v in self.scores.values() if isinstance(v, (int, float))]
        return sum(numeric) / len(numeric) if numeric else None

    def __repr__(self):
        return f"Scorecard({self.scores})"
