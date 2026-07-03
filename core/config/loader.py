import os
import yaml
from typing import Any, Dict, Optional


class ConfigLoader:
    """Consolidated configuration loader for runtime, agents, models, and dashboard."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_config(self, name: str) -> Dict[str, Any]:
        """Loads and returns the configuration file with the given name."""
        if name in self._cache:
            return self._cache[name]

        file_path = os.path.join(self.config_dir, f"{name}.yaml")
        if not os.path.exists(file_path):
            # Fallback to an empty dictionary to prevent crash
            return {}

        try:
            with open(file_path, "r") as f:
                content = yaml.safe_load(f) or {}
            self._cache[name] = content
            return content
        except Exception:
            return {}

    def get_value(self, config_name: str, key_path: str, default: Any = None) -> Any:
        """Retrieves a configuration value using dot-notation.
        
        Example: get_value("models", "providers.gemini.model_name")
        """
        config = self.get_config(config_name)
        parts = key_path.split(".")
        current = config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current
