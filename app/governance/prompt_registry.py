import json
from pathlib import Path
from typing import Any

from app.governance.model_registry import ModelRegistry
from app.governance.validation import validate_prompt_registry

REGISTRY_DIR = Path(__file__).resolve().parent / "registry"


class PromptRegistry:
    _registry_data: dict[str, Any] = {}

    @classmethod
    def load(cls):
        path = REGISTRY_DIR / "prompts_v2.json"
        if not path.exists():
            raise FileNotFoundError(f"Prompt registry file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        validate_prompt_registry(data)
        cls._registry_data = data

    @classmethod
    def get_prompt_config(cls, agent_name: str) -> dict[str, Any]:
        if not cls._registry_data:
            cls.load()
        prompts = cls._registry_data.get("prompts", {})
        if agent_name not in prompts:
            raise ValueError(f"Prompt configuration for agent '{agent_name}' not found.")
        return prompts[agent_name]

    @classmethod
    def get_active_version(cls, agent_name: str) -> str:
        config = cls.get_prompt_config(agent_name)
        return config["active_version"]

    @classmethod
    def get_version_details(cls, agent_name: str, version: str) -> dict[str, Any]:
        config = cls.get_prompt_config(agent_name)
        versions = config.get("versions", {})
        if version not in versions:
            raise ValueError(f"Version '{version}' not found for agent prompt '{agent_name}'.")
        return versions[version]

    @classmethod
    def validate_prompt_model_compatibility(cls, agent_name: str, model_name: str):
        config = cls.get_prompt_config(agent_name)
        active_ver = config["active_version"]
        details = cls.get_version_details(agent_name, active_ver)

        # Check model name compatibility
        compatible_models = details.get("compatible_models", [])
        if model_name not in compatible_models:
            raise ValueError(
                f"Model '{model_name}' is not compatible with prompt '{agent_name}' ({active_ver}). Compatible models: {compatible_models}"
            )

        # Check capability matrix
        if details.get("requires_structured_output"):
            if not ModelRegistry.check_capabilities(model_name, ["structured_output"]):
                raise ValueError(
                    f"Model '{model_name}' lacks capability 'structured_output' required by prompt '{agent_name}' ({active_ver})."
                )


PromptRegistry.load()
