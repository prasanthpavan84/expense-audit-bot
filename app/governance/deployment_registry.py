import json
import os
from pathlib import Path
from typing import Any

from app.governance.validation import validate_deployment_registry

REGISTRY_DIR = Path(__file__).resolve().parent / "registry"


class DeploymentRegistry:
    _registry_data: dict[str, Any] = {}

    @classmethod
    def load(cls):
        path = REGISTRY_DIR / "deployments_v1.json"
        if not path.exists():
            raise FileNotFoundError(f"Deployment registry file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        validate_deployment_registry(data)
        cls._registry_data = data

    @classmethod
    def get_environment_config(cls, env_name: str) -> dict[str, Any]:
        if not cls._registry_data:
            cls.load()
        envs = cls._registry_data.get("environments", {})
        if env_name not in envs:
            raise ValueError(f"Deployment environment '{env_name}' not found in registry.")
        return envs[env_name]

    @classmethod
    def validate_environment(cls, env_name: str) -> bool:
        config = cls.get_environment_config(env_name)
        secrets = config.get("secrets_required", [])
        for secret in secrets:
            if secret not in os.environ and not os.getenv("MOCK_LLM", "True").lower() == "true":
                # Only fail on missing secrets in production/live API runs
                raise ValueError(f"Required secret '{secret}' is missing from environment in '{env_name}' mode.")
        return True


DeploymentRegistry.load()
