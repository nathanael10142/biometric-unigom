import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = f"ws_{id(websocket)}"
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Ping/pong heartbeat
            data = await websocket.receive_text()
            await manager.broadcast({"type": "ping", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.debug(f"[WS] Client {client_id} disconnected")

