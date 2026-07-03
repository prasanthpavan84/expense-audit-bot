# app/registry/agent_registry.py
"""Agent Registry
Loads agent metadata from `config/agents.yaml` and discovers entry‑points.
Provides a singleton `AgentRegistry` with lookup helpers.
"""
import os
import yaml
import importlib
from typing import Dict, Any

class AgentMeta:
    def __init__(self, agent_id: str, version: str, description: str, class_path: str,
                 max_concurrency: int = 5, timeout_seconds: float = 30.0,
                 retry_policy: Dict[str, Any] = None):
        self.agent_id = agent_id
        self.version = version
        self.description = description
        self.class_path = class_path
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or {"max_attempts": 3, "backoff_factor": 1.5}

    def __repr__(self) -> str:
        return f"AgentMeta({self.agent_id!r}, v{self.version})"

    @property
    def agent_class(self):
        """Lazily import and return the concrete agent class.
        The class must implement an async ``process_state(state)`` method.
        """
        module_path, _, class_name = self.class_path.rpartition('.')
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

class AgentRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load agents from `config/agents.yaml`.
        The file is optional – if missing we start with an empty registry.
        """
        self._agents: Dict[str, AgentMeta] = {}
        config_path = os.path.join(os.getcwd(), "config", "agents.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for aid, meta in data.get("agents", {}).items():
                self._agents[aid] = AgentMeta(
                    agent_id=aid,
                    version=str(meta.get("version", "1.0")),
                    description=meta.get("description", ""),
                    class_path=meta.get("class_path"),
                    max_concurrency=int(meta.get("max_concurrency", 5)),
                    timeout_seconds=float(meta.get("timeout_seconds", 30.0)),
                    retry_policy=meta.get("retry_policy"),
                )
        # Future extension: discover entry‑points via plugin_loader

    def get(self, agent_id: str) -> AgentMeta:
        return self._agents.get(agent_id)

    def list_all(self) -> Dict[str, AgentMeta]:
        return dict(self._agents)

# Export a ready‑to‑use singleton for imports throughout the codebase
agent_registry = AgentRegistry()
