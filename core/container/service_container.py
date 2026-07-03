import dataclasses
from typing import Any, Dict

class ServiceContainer:
    """Simple dependency injection container for core services.

    Example usage:
        services = ServiceContainer(config=my_config)
        ocr_agent = OCRAgent(services)
    """

    def __init__(self, **services: Any):
        # Store provided services as attributes.
        for name, service in services.items():
            setattr(self, name, service)

    def register(self, name: str, instance: Any) -> None:
        """Register a new service instance.

        Args:
            name: Attribute name to expose on the container.
            instance: Service instance.
        """
        setattr(self, name, instance)

    def get(self, name: str) -> Any:
        """Retrieve a registered service by name.
        """
        return getattr(self, name)
