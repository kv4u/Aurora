"""WebSocket endpoint for real-time AURORA dashboard updates."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.security.auth import verify_token

logger = logging.getLogger("aurora.ws")

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections.remove(ws)

    async def send_portfolio_update(self, data: dict):
        await self.broadcast({"type": "portfolio_update", "payload": data})

    async def send_signal(self, data: dict):
        await self.broadcast({"type": "new_signal", "payload": data})

    async def send_trade(self, data: dict):
        await self.broadcast({"type": "trade_executed", "payload": data})

    async def send_risk_alert(self, data: dict):
        await self.broadcast({"type": "risk_alert", "payload": data})

    async def send_circuit_breaker(self, data: dict):
        await self.broadcast({"type": "circuit_breaker", "payload": data})


# Global manager instance
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket connection with optional JWT authentication."""
    # Extract token from query params
    token = websocket.query_params.get("token")
    if token:
        settings = get_settings()
        username = verify_token(token, settings.jwt_secret.get_secret_value())
        if not username:
            await websocket.close(code=4001, reason="Invalid token")
            return

    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()

            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)
