# Memory package placeholder

"""In‑memory data stores for the expense audit bot.

These classes will later be replaced or extended with durable storage
(e.g., SQLite, Redis) but for now they provide simple Python containers.
"""

class ReceiptMemory:
    """Store parsed receipt objects for the current workflow."""
    def __init__(self):
        self.receipts = []

    def add(self, receipt):
        self.receipts.append(receipt)

    def get_all(self):
        return list(self.receipts)

class ConversationMemory:
    """Track conversation turns and intents."""
    def __init__(self):
        self.turns = []

    def add_turn(self, user_input, intent, entities):
        self.turns.append({"user_input": user_input, "intent": intent, "entities": entities})

    def history(self):
        return list(self.turns)
