
import asyncio
from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.connections: dict[int, set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, group_id: int, websocket: WebSocket):
        async with self.lock:
            self.connections[group_id].add(websocket)

    async def disconnect(self, group_id: int, websocket: WebSocket):
        async with self.lock:
            sockets = self.connections.get(group_id)

            if sockets:
                sockets.discard(websocket)

                if not sockets:
                    self.connections.pop(group_id, None)

    async def broadcast(self, group_id: int, event: dict):
        async with self.lock:
            clients = list(self.connections.get(group_id, set()))

        for client in clients:
            try:
                await client.send_json(event)
            except Exception:
                await self.disconnect(group_id, client)


websocket_manager = WebSocketManager()
