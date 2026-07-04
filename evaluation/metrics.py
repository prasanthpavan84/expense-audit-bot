"""evaluation/metrics.py

Provides simple metric classes for evaluating artifacts produced by the Expense Audit Bot.
"""

class Metric:
    """Base class for all metrics."""
    def compute(self, data):
        raise NotImplementedError

class AccuracyMetric(Metric):
    """Placeholder accuracy metric (example)."""
    def compute(self, predictions, targets):
        correct = sum(p == t for p, t in zip(predictions, targets))
        return correct / len(targets) if targets else 0
