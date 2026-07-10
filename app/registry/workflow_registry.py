# app/registry/workflow_registry.py
"""Workflow Registry
Loads workflow definitions from `config/workflows.yaml`.
Each workflow defines a DAG of agent nodes and directed edges.
Provides a singleton `WorkflowRegistry` with lookup helpers.
"""

import os
from typing import Any

import yaml


class WorkflowSpec:
    def __init__(
        self,
        workflow_id: str,
        version: str,
        nodes: dict[str, dict],
        edges: list[tuple[str, str]],
        parallel_groups: list[list[str]] = None,
        retries: int = 0,
        timeout_seconds: Any = None,
    ):
        self.workflow_id = workflow_id
        self.version = version
        self.nodes = nodes  # node_id -> metadata (agent, version, etc.)
        self.edges = edges  # list of (from, to)
        self.parallel_groups = parallel_groups or []
        self.retries = retries
        self.timeout_seconds = timeout_seconds

    def __repr__(self) -> str:
        return f"WorkflowSpec({self.workflow_id!r}, v{self.version})"


class WorkflowRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load workflows from `config/workflows.yaml`.
        The file is optional – if missing we start with an empty registry.
        """
        self._workflows: dict[str, WorkflowSpec] = {}
        config_path = os.path.join(os.getcwd(), "config", "workflows.yaml")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for wid, spec in data.get("workflows", {}).items():
                self._workflows[wid] = WorkflowSpec(
                    workflow_id=wid,
                    version=str(spec.get("version", "1.0")),
                    nodes=spec.get("nodes", {}),
                    edges=[tuple(e) for e in spec.get("edges", [])],
                    parallel_groups=spec.get("parallel_groups", []),
                    retries=int(spec.get("retries", 0)),
                    timeout_seconds=spec.get("timeout_seconds"),
                )

    def get(self, workflow_id: str) -> WorkflowSpec:
        return self._workflows.get(workflow_id)

    def list_all(self) -> dict[str, WorkflowSpec]:
        return dict(self._workflows)


# Export a ready‑to‑use singleton
workflow_registry = WorkflowRegistry()
