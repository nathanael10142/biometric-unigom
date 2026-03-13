import json
import logging
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        if client_id is None:
            client_id = f"client_{id(websocket)}"
        self.active_connections[client_id] = websocket
        logger.info(f"[WS] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        del self.active_connections[client_id]
        logger.info(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """Broadcast to all active clients"""
        message = json.dumps(data)
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)

manager = ConnectionManager()

