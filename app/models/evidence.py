"""Structured Evidence Model for the AI Cognitive Layer.

Defines the structure for evidence objects used to trace and justify
the decisions made by agents during execution.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any

from app.models.state import WorkflowState


@dataclass
class Evidence:
    """Represents a discrete piece of evidence supporting a conclusion."""

    source: str
    field: str
    value: Any
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    origin_agent: str = "unknown"
    validated: bool = False


class EvidenceCollector:
    """Utility class to collect and query evidence from workflow state."""

    @staticmethod
    def get_or_create_evidence_list(state: WorkflowState) -> list[dict[str, Any]]:
        """Retrieves or initializes the evidence list in state metadata."""
        if "evidence" not in state.metadata:
            state.metadata["evidence"] = []
        return state.metadata["evidence"]

    @classmethod
    def add(
        cls,
        state: WorkflowState,
        source: str,
        field_name: str,
        value: Any,
        confidence: float,
        origin_agent: str,
        validated: bool = False,
    ) -> None:
        """Adds a new piece of evidence to the state."""
        evidence_list = cls.get_or_create_evidence_list(state)

        # Create Evidence dataclass instance
        ev = Evidence(
            source=source,
            field=field_name,
            value=value,
            confidence=round(confidence, 3),
            origin_agent=origin_agent,
            validated=validated,
        )

        # Store as dict in state metadata for serialization and downstream compatibility
        evidence_list.append(ev.__dict__)

    @classmethod
    def get_for_field(cls, state: WorkflowState, field_name: str) -> list[dict[str, Any]]:
        """Retrieves all evidence associated with a specific field name."""
        evidence_list = cls.get_or_create_evidence_list(state)
        return [ev for ev in evidence_list if ev.get("field") == field_name]

    @classmethod
    def get_by_source(cls, state: WorkflowState, source: str) -> list[dict[str, Any]]:
        """Retrieves all evidence gathered from a specific source."""
        evidence_list = cls.get_or_create_evidence_list(state)
        return [ev for ev in evidence_list if ev.get("source") == source]

    @classmethod
    def verify_evidence(cls, state: WorkflowState, field_name: str, expected_val: Any) -> bool:
        """Validates that a matching piece of evidence exists."""
        evs = cls.get_for_field(state, field_name)
        for ev in evs:
            if ev.get("value") == expected_val:
                ev["validated"] = True
                return True
        return False
