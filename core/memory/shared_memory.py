# Shared memory façade

"""Aggregates individual memory components into a single shared
instance that can be passed around via the ServiceContainer.

Later this can be extended with transaction semantics, persistence, and
snapshot/rollback capabilities.
"""

from . import ReceiptMemory, ConversationMemory

class SharedMemory:
    """Facade aggregating all in‑memory stores.

    Agents can access ``shared_memory.receipt`` or ``shared_memory.conversation``
    to read/write state. Additional memories can be added as attributes.
    """

    def __init__(self) -> None:
        self.receipt = ReceiptMemory()
        self.conversation = ConversationMemory()

    # Example helper methods could be added here, e.g., clear_all, snapshot, etc.
