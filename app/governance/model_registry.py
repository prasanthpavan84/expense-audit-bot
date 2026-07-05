import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from app.governance.validation import validate_model_registry

REGISTRY_DIR = Path(__file__).resolve().parent / "registry"

class ModelRegistry:
    _registry_data: Dict[str, Any] = {}
    
    @classmethod
    def load(cls):
        path = REGISTRY_DIR / "models_v1.json"
        if not path.exists():
            raise FileNotFoundError(f"Model registry file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate_model_registry(data)
        cls._registry_data = data
        
    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        if not cls._registry_data:
            cls.load()
        models = cls._registry_data.get("models", {})
        if model_name not in models:
            raise ValueError(f"Model '{model_name}' not found in registry.")
        return models[model_name]
        
    @classmethod
    def resolve_model(cls, model_name: str) -> str:
        """Resolves active model name or its fallback if needed."""
        try:
            config = cls.get_model_config(model_name)
            return model_name
        except ValueError as e:
            # Check fallback or default
            return "gemini-2.0-flash"
            
    @classmethod
    def check_capabilities(cls, model_name: str, required_caps: list[str]) -> bool:
        config = cls.get_model_config(model_name)
        caps = config.get("capabilities", {})
        return all(caps.get(cap, False) for cap in required_caps)

ModelRegistry.load()
