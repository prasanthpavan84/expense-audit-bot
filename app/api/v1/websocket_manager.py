from fastapi import WebSocket


class ConsoleWebSocketManager:
    """Manages active WebSocket connections for streaming real-time console events."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might have dropped, will get removed on disconnect
                pass


manager = ConsoleWebSocketManager()


# Hook into the EventBus to automatically broadcast all engine events
def subscribe_event_bus_to_websockets():
    import asyncio

    from app.core.event_bus import EventBus

    bus = EventBus()

    def handle_event(event_name: str, payload: dict):
        # Schedule the coroutine execution on the main loop
        loop = asyncio.get_event_loop()
        message = {"event": event_name, "payload": payload}
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)

    # Subscribe to all key console events
    for event in ["WorkflowStarted", "AgentStarted", "AgentCompleted", "AgentFailed", "WorkflowCompleted"]:
        bus.subscribe(event, lambda p, ev=event: handle_event(ev, p))
