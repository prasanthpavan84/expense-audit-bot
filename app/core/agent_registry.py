from typing import Dict, List
from app.core.agent_base import BaseExpenseAgent
import json
from pathlib import Path

_CAPABILITIES_PATH = Path(__file__).resolve().parent / "agent_capabilities.json"
with open(_CAPABILITIES_PATH, "r", encoding="utf-8") as f:
    AGENT_CAPABILITIES = json.load(f)

class AgentRegistry:
    """Registry to manage and retrieve agent instances."""
    _agents: Dict[str, BaseExpenseAgent] = {}

    @classmethod
    def register(cls, name: str, agent: BaseExpenseAgent):
        """Register an agent instance by name."""
        cls._agents[name] = agent

    @classmethod
    def get_agent(cls, name: str) -> BaseExpenseAgent:
        """Retrieve an agent by name."""
        if name not in cls._agents:
            raise ValueError(f"Agent '{name}' not found in registry.")
        return cls._agents[name]

    @classmethod
    def get_agents_for_capability(cls, capability: str) -> List[str]:
        """Return list of agent names that provide the given capability."""
        return [agent for agent, caps in AGENT_CAPABILITIES.items() if capability in caps]

    @classmethod
    def clear(cls):
        """Clear the registry (useful for testing)."""
        cls._agents.clear()

registry = AgentRegistry()
