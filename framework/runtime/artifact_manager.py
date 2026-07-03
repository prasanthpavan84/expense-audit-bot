# framework/runtime/artifact_manager.py
"""A minimal ArtifactManager implementation for the prototype.

It satisfies :class:`ArtifactManagerInterface` by creating a temporary
execution directory and writing JSON‑serialisable artifacts to files within
that directory.  The implementation is deliberately simple – it uses the
standard library only and can be replaced later with a more robust storage
backend.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .interfaces import ArtifactManagerInterface


class SimpleArtifactManager(ArtifactManagerInterface):
    """Store artifacts on the local filesystem under a temporary directory.

    Each call to :meth:`create_execution_bundle` creates a new unique directory
    (named after the ``run_id``) inside the system's temporary folder.  The
    directory path is returned so callers can reference it later.
    """

    def __init__(self) -> None:
        # Base temporary root – shared across runs.
        self._base_dir = Path(tempfile.gettempdir()) / "expense_audit_artifacts"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def create_execution_bundle(self, run_id: str) -> str:
        """Create a sub‑directory for ``run_id`` and return its absolute path.
        """
        run_dir = self._base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return str(run_dir)

    def write_artifact(self, path: str, filename: str, data: Any) -> None:
        """Write ``data`` to ``filename`` inside ``path``.

        ``data`` is JSON‑serialisable; it is written with ``json.dump`` using
        ``ensure_ascii=False`` for readability.
        """
        full_path = Path(path) / filename
        # Ensure the parent directory exists (should, but guard anyway).
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

__all__ = ["SimpleArtifactManager"]
