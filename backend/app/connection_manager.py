"""
Alakoro FiberSense - WebSocket Connection Manager
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerenciador de conexoes WebSocket."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._counter = 0

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        self._counter += 1
        conn_id = f"ws_{self._counter}"
        self._connections[conn_id] = websocket
        logger.info(f"WebSocket connected: {conn_id} (total: {len(self._connections)})")
        return conn_id

    def disconnect(self, conn_id: str):
        if conn_id in self._connections:
            del self._connections[conn_id]
            logger.info(f"WebSocket disconnected: {conn_id} (total: {len(self._connections)})")

    async def send_message(self, conn_id: str, message: dict):
        if conn_id in self._connections:
            try:
                await self._connections[conn_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {conn_id}: {e}")
                self.disconnect(conn_id)

    async def broadcast(self, message: dict, signal_type: str = None):
        """Broadcast message to all or filtered by signal_type."""
        dead_connections = []
        for conn_id, ws in self._connections.items():
            try:
                if signal_type is None or ws.scope.get("signal_type") == signal_type:
                    await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {conn_id}: {e}")
                dead_connections.append(conn_id)

        for conn_id in dead_connections:
            self.disconnect(conn_id)

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Global instance
manager = ConnectionManager()
