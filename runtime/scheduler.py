"""runtime/scheduler.py

Implements a simple asynchronous task scheduler for agents.
"""
import asyncio
from typing import Callable, Awaitable, Any, List

class Scheduler:
    """Basic async scheduler that can run coroutines concurrently and schedule periodic tasks."""
    def __init__(self) -> None:
        self._tasks: List[asyncio.Task] = []
        self._loop = asyncio.get_event_loop()

    def schedule(self, coro: Awaitable[Any]) -> asyncio.Task:
        """Schedule a coroutine to run immediately."""
        task = self._loop.create_task(coro)
        self._tasks.append(task)
        return task

    async def run_periodic(self, interval_seconds: float, func: Callable[[], Awaitable[Any]]) -> None:
        """Run `func` repeatedly every `interval_seconds` seconds."""
        while True:
            await func()
            await asyncio.sleep(interval_seconds)

    async def run_concurrent(self, coros: List[Awaitable[Any]]) -> None:
        """Run multiple coroutines concurrently using asyncio.gather."""
        await asyncio.gather(*coros)

    async def shutdown(self) -> None:
        """Cancel all scheduled tasks gracefully."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
