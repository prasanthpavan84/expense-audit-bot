"""evaluation/evaluator.py

Simple evaluator that runs configured metrics against artifact data.
"""

from .metrics import Metric

class Evaluator:
    """Runs a collection of Metric instances on provided data.

    The `evaluate` method returns a dict mapping metric class names to their computed values.
    """
    def __init__(self, metrics: list[Metric] | None = None):
        self.metrics = metrics or []

    def add_metric(self, metric: Metric) -> None:
        self.metrics.append(metric)

    def evaluate(self, **data) -> dict:
        results = {}
        for metric in self.metrics:
            # Each metric may expect different kwargs; we pass all and let it handle.
            try:
                # Assume metric.compute signature matches provided data.
                result = metric.compute(**data)
            except TypeError:
                # Fallback: try positional args if metric expects specific parameters.
                result = metric.compute(*data.values())
            results[metric.__class__.__name__] = result
        return results
