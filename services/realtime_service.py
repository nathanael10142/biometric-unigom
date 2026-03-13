"""
Real-time Service - Meta-inspired WebSocket service for live updates
Handles real-time dashboard updates, notifications, and live attendance
"""

import logging
import asyncio
import json
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import websockets
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger("realtime-service")

# Real-time service
realtime_service = FastAPI(
    title="Real-time Service",
    description="Meta-inspired real-time WebSocket service",
    version="1.0.0"
)

realtime_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """Meta-style WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[WebSocket, str] = {}
        self.room_connections: Dict[WebSocket, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.user_connections[websocket] = user_id
        self.room_connections[websocket] = set()
        
        logger.info(f"User {user_id} connected. Total connections: {len(self.user_connections)}")
        
        # Send welcome message
        await self.send_to_user(user_id, {
            "type": "connection",
            "message": "Connected to real-time service",
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        user_id = self.user_connections.get(websocket)
        if user_id:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            del self.user_connections[websocket]
            if websocket in self.room_connections:
                del self.room_connections[websocket]
            
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.user_connections)}")
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def send_to_room(self, room: str, message: Dict[str, Any]):
        """Send message to all users in a room"""
        for websocket, rooms in self.room_connections.items():
            if room in rooms:
                user_id = self.user_connections.get(websocket)
                if user_id:
                    await self.send_to_user(user_id, message)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected users"""
        for user_id in self.active_connections:
            await self.send_to_user(user_id, message)
    
    async def join_room(self, websocket: WebSocket, room: str):
        """Add user to a room"""
        if websocket not in self.room_connections:
            self.room_connections[websocket] = set()
        self.room_connections[websocket].add(room)
        
        user_id = self.user_connections.get(websocket)
        logger.info(f"User {user_id} joined room: {room}")
    
    async def leave_room(self, websocket: WebSocket, room: str):
        """Remove user from a room"""
        if websocket in self.room_connections:
            self.room_connections[websocket].discard(room)
        
        user_id = self.user_connections.get(websocket)
        logger.info(f"User {user_id} left room: {room}")

class RealtimeEventEmitter:
    """Meta-style event emitter for real-time updates"""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.event_handlers = {}
        self.running = False
    
    def on(self, event_type: str, handler):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def emit(self, event_type: str, data: Dict[str, Any], target: Optional[str] = None):
        """Emit event to subscribers"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if target:
            await self.manager.send_to_user(target, event)
        else:
            await self.manager.broadcast(event)
        
        # Call registered handlers
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
    
    async def start_simulation(self):
        """Start real-time data simulation"""
        self.running = True
        logger.info("Starting real-time simulation...")
        
        while self.running:
            try:
                # Simulate attendance updates
                await self.emit("attendance_update", {
                    "employee_id": f"EMP_{datetime.now().second}",
                    "status": "present",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Simulate dashboard metrics updates
                await self.emit("metrics_update", {
                    "attendance_rate": 85.5 + (datetime.now().second % 10),
                    "present_count": 42 + (datetime.now().second % 5),
                    "late_count": 3 + (datetime.now().second % 3),
                    "absent_count": 2
                }, target="dashboard")
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in simulation: {e}")
                await asyncio.sleep(5)

# Initialize connection manager and event emitter
manager = ConnectionManager()
event_emitter = RealtimeEventEmitter(manager)

@realtime_service.on_event("startup")
async def startup_event():
    """Initialize real-time service"""
    logger.info("Starting Real-time WebSocket Service...")
    
    # Start simulation in background
    asyncio.create_task(event_emitter.start_simulation())

@realtime_service.on_event("shutdown")
async def shutdown_event():
    """Shutdown real-time service"""
    event_emitter.running = False
    logger.info("Real-time service shutdown")

@realtime_service.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "realtime-websocket",
        "active_connections": len(manager.user_connections),
        "active_users": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

@realtime_service.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """Main WebSocket endpoint"""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "join_room":
                room = message.get("room")
                if room:
                    await manager.join_room(websocket, room)
                    await manager.send_to_user(user_id, {
                        "type": "room_joined",
                        "room": room,
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif message_type == "leave_room":
                room = message.get("room")
                if room:
                    await manager.leave_room(websocket, room)
                    await manager.send_to_user(user_id, {
                        "type": "room_left",
                        "room": room,
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif message_type == "ping":
                await manager.send_to_user(user_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            else:
                # Echo back unknown messages
                await manager.send_to_user(user_id, {
                    "type": "echo",
                    "original_message": message,
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@realtime_service.post("/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all connected clients"""
    await manager.broadcast({
        "type": "broadcast",
        "data": message,
        "timestamp": datetime.now().isoformat()
    })
    return {"message": "Broadcast sent", "timestamp": datetime.now().isoformat()}

@realtime_service.post("/send/{user_id}")
async def send_to_user(user_id: str, message: Dict[str, Any]):
    """Send message to specific user"""
    await manager.send_to_user(user_id, {
        "type": "direct_message",
        "data": message,
        "timestamp": datetime.now().isoformat()
    })
    return {"message": f"Message sent to {user_id}", "timestamp": datetime.now().isoformat()}

@realtime_service.post("/room/{room}")
async def send_to_room(room: str, message: Dict[str, Any]):
    """Send message to all users in a room"""
    await manager.send_to_room(room, {
        "type": "room_message",
        "data": message,
        "room": room,
        "timestamp": datetime.now().isoformat()
    })
    return {"message": f"Message sent to room {room}", "timestamp": datetime.now().isoformat()}

@realtime_service.get("/stats")
async def get_connection_stats():
    """Get connection statistics"""
    return {
        "active_connections": len(manager.user_connections),
        "active_users": len(manager.active_connections),
        "user_details": {
            user_id: len(connections) 
            for user_id, connections in manager.active_connections.items()
        },
        "timestamp": datetime.now().isoformat()
   }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(realtime_service, host="0.0.0.0", port=8007)
