# framework/runtime/__init__.py
"""Runtime package exposing the core execution engine and supporting components.

This module aggregates the foundational pieces required by every other layer:
- RuntimeEngine, RuntimeContext, StateManager
- EventBus (MessageBus)
- Scheduler (ThreadScheduler)
- ArtifactManager (SimpleArtifactManager)
- SharedMemory (KeyValueMemory, VectorMemory)
- Registry (for agents & workflows)
"""

from .runtime_engine import RuntimeEngine
from .runtime_context import RuntimeContext
from .runtime_state import RuntimeState, RuntimeStateMachine
from .state_manager import StateManager
from .exceptions import RuntimeError, InvalidStateTransitionError
from .interfaces import SchedulerInterface, PlannerInterface, ArtifactManagerInterface

# Additional core components
from core.event_bus.message_bus import MessageBus
from .thread_scheduler import ThreadScheduler
from .artifact_manager import SimpleArtifactManager
from .shared_memory import KeyValueMemory, VectorMemory
from .registry import Registry

__all__ = [
    "RuntimeEngine",
    "RuntimeContext",
    "RuntimeState",
    "RuntimeStateMachine",
    "StateManager",
    "RuntimeError",
    "InvalidStateTransitionError",
    "SchedulerInterface",
    "PlannerInterface",
    "ArtifactManagerInterface",
    "MessageBus",
    "ThreadScheduler",
    "SimpleArtifactManager",
    "KeyValueMemory",
    "VectorMemory",
    "Registry",
]
