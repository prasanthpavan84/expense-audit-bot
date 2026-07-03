# core/artifact_manager/__init__.py
"""Simple artifact manager for the expense audit bot.

It satisfies the ``ArtifactManagerInterface`` required by ``RuntimeEngine``.
The implementation stores artifacts under a ``runs/`` directory inside the
project workspace. Each execution gets its own sub‑directory identified by a
run ID (e.g., ``run_001``). Artifacts are written as JSON when the data is a
Python ``dict``/``list``; otherwise the raw string representation is persisted.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ...framework.runtime.interfaces import ArtifactManagerInterface


class SimpleArtifactManager(ArtifactManagerInterface):
    """Filesystem‑backed artifact manager.

    The manager creates a ``runs`` directory at the project root (the first
    ancestor containing a ``pyproject.toml`` or ``setup.cfg``). For simplicity
    we create it relative to the current working directory.
    """

    def __init__(self, base_dir: str | os.PathLike = "runs") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_execution_bundle(self, run_id: str) -> str:
        """Create a directory for a new execution and return its path.

        Parameters
        ----------
        run_id: str
            Identifier for the execution (e.g., ``run_001``).
        """
        bundle_path = self.base_dir / run_id
        bundle_path.mkdir(parents=True, exist_ok=True)
        return str(bundle_path)

    def write_artifact(self, path: str, filename: str, data: Any) -> None:
        """Write ``data`` to ``filename`` inside ``path``.

        If ``data`` is JSON‑serialisable (dict or list), it is stored as a
        ``.json`` file; otherwise its ``str`` representation is written.
        """
        full_path = Path(path) / filename
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (dict, list)):
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(str(data))
