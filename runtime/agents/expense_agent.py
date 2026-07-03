"""runtime/agents/expense_agent.py

A simple example agent that processes expense audit requests.
"""
import asyncio
from .base_agent import BaseAgent
from ..event_bus import EventBus

class ExpenseAgent(BaseAgent):
    """Concrete agent that simulates expense auditing.

    The `process` method pretends to evaluate an expense request and emits an
    `expense_audited` event via the provided EventBus.
    """
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def process(self, request: dict) -> dict:
        # Simulate some async work
        await asyncio.sleep(0.1)
        result = {"status": "audited", "request": request}
        # Publish an event for listeners
        self.event_bus.publish("expense_audited", result)
        return result

    async def execute(self):
        """Entry point for the scheduler – processes a demo request.
        """
        sample_request = {"amount": 123.45, "category": "Travel", "description": "Taxi"}
        await self.process(sample_request)
