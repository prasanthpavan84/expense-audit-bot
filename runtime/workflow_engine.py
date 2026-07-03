'''Workflow Engine

Coordinates execution of agents using the Scheduler.
'''

import asyncio
from .scheduler import Scheduler

class WorkflowEngine:
    def __init__(self, scheduler: Scheduler = None):
        self.scheduler = scheduler or Scheduler()
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(agent)

    async def run(self):
        """Execute all registered agents concurrently using asyncio.gather."""
        # Collect coroutines from agents' execute methods
        coros = [agent.execute() for agent in self.agents]
        if coros:
            await asyncio.gather(*coros)
