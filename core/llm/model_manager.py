import os
import yaml
from typing import Dict, Any, Optional
from .provider import LLMProvider, MockProvider


class ModelManager:
    """Manages LLM providers based on application configuration.
    
    Acts as a central registry to fetch configured models or providers.
    """

    def __init__(self, config_path: Optional[str] = None):
        self._providers: Dict[str, LLMProvider] = {}
        self._default_provider_name: str = "mock"
        
        # Register default mock provider
        self.register_provider("mock", MockProvider())
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Register a model provider under a name."""
        self._providers[name] = provider

    def load_config(self, config_path: str) -> None:
        """Load provider configurations from a YAML file."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Example structure of models.yaml:
            # default_provider: gemini
            # providers:
            #   gemini:
            #     class: GeminiProvider
            #     api_key: ...
            
            if config:
                self._default_provider_name = config.get("default_provider", "mock")
                # Providers setup can be done dynamically here in a full implementation.
        except Exception:
            # Fall back to default mock registry if parsing fails
            pass

    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """Retrieve a registered provider by name.
        
        If name is None, returns the configured default provider.
        """
        provider_name = name or self._default_provider_name
        provider = self._providers.get(provider_name)
        if not provider:
            # Fallback to mock provider to avoid crash
            return self._providers["mock"]
        return provider
