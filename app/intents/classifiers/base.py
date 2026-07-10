"""Base Intent Classifier — plugin interface for ensemble voting.

Every concrete classifier implements ``classify()`` and returns a
``ClassifierVote``.  The ensemble aggregates all votes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassifierVote:
    """A single classifier's vote — immutable."""

    classifier_name: str
    stage1_category: str  # Conversation, Expense, Question, Command, Unknown
    stage2_intent: str  # Greeting, Audit, Policy, etc.
    confidence: float
    reason: str
    matched_evidence: tuple = ()  # what matched
    negative_evidence: tuple = ()  # what was explicitly rejected


class BaseIntentClassifier(ABC):
    """Plugin interface — all ensemble classifiers extend this."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique classifier name used in voting."""
        ...

    @property
    def weight(self) -> float:
        """Weight of this classifier in the ensemble vote. Default 1.0."""
        return 1.0

    @abstractmethod
    def classify(self, text: str, **context) -> ClassifierVote:
        """Classify the input and return a vote."""
        ...
