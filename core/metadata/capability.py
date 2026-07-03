from typing import List, Any


def capability(
    name: str,
    version: str,
    inputs: List[str],
    outputs: List[str],
    priority: int = 0,
    **extra: Any,
) -> Any:
    """Decorator to attach capability metadata to an agent class."""
    def wrapper(cls: Any) -> Any:
        cls.__capability__ = {
            "name": name,
            "version": version,
            "inputs": inputs,
            "outputs": outputs,
            "priority": priority,
            **extra,
        }
        return cls
    return wrapper
