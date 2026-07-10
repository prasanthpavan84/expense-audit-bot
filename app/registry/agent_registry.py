import importlib
import os
from typing import Any

import yaml


class AgentMeta:
    def __init__(
        self,
        agent_id: str,
        version: str,
        description: str,
        class_path: str,
        max_concurrency: int = 5,
        timeout_seconds: float = 30.0,
        retry_policy: dict[str, Any] = None,
    ):
        self.agent_id = agent_id
        self.version = version
        self.description = description
        self.class_path = class_path
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or {"max_attempts": 3, "backoff_factor": 1.5}

    @property
    def agent_class(self):
        """Lazily import and return the concrete agent class."""
        module_path, _, class_name = self.class_path.rpartition(".")
        module = importlib.import_module(module_path)
        return getattr(module, class_name)


class AgentRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
            cls._instance._instances = {}
        return cls._instance

    def _load(self):
        self._agents: dict[str, AgentMeta] = {}
        config_path = os.path.join(os.getcwd(), "config", "agents.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
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
            except Exception:
                pass

    def get(self, agent_id: str) -> AgentMeta | None:
        return self._agents.get(agent_id)

    def list_all(self) -> dict[str, AgentMeta]:
        return dict(self._agents)

    def get_agent(self, agent_id: str) -> Any:
        """Helper to get a cached instance of the agent."""
        if agent_id in self._instances:
            return self._instances[agent_id]

        meta = self.get(agent_id)
        if not meta:
            # Fallback direct discovery of standard names
            fallback_map = {
                "planner_agent": "app.agents.planner_agent.PlannerAgent",
                "receipt_extractor": "app.agents.receipt_agent.ReceiptAgent",
                "policy_agent": "app.agents.policy_agent.PolicyAgent",
                "fraud_agent": "app.agents.fraud_agent.FraudAgent",
                "reasoning_agent": "app.agents.reasoning_agent.ReasoningAgent",
                "reflection_agent": "app.agents.reflection_agent.ReflectionAgent",
                "report_agent": "app.agents.report_agent.ReportAgent",
            }
            if agent_id in fallback_map:
                meta = AgentMeta(agent_id, "1.0.0", "", fallback_map[agent_id])
            else:
                return None

        try:
            instance = meta.agent_class()
            self._instances[agent_id] = instance
            return instance
        except Exception as e:
            print(f"FAILED TO LOAD AGENT '{agent_id}': {e}")
            raise e


# Export singleton
agent_registry = AgentRegistry()
