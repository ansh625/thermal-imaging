"""
websocket_manager.py — Event WebSocket Manager
═══════════════════════════════════════════════════════════════════════════════
Manages non-video WebSocket connections used for event notifications
(detection alerts, camera status, system events).

Video streaming is handled separately by workers/stream_worker.py.
These two systems share zero state.
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        # user_id → list of open WebSocket connections
        self._connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info(
            f"[WSManager] User {user_id} connected "
            f"(total={len(self._connections[user_id])})"
        )

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)
        logger.info(f"[WSManager] User {user_id} disconnected")

    async def send(self, user_id: int, message: dict) -> None:
        """Send a message to ALL connections for user_id."""
        conns = self._connections.get(user_id, [])
        dead: List[WebSocket] = []

        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception as exc:
                logger.warning(f"[WSManager] Send failed for user {user_id}: {exc}")
                dead.append(ws)

        for ws in dead:
            conns.remove(ws)

    async def broadcast(self, user_id: int, event_type: str, data: dict) -> None:
        """Convenience wrapper that wraps data in the standard envelope."""
        await self.send(
            user_id,
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


# Module-level singleton
websocket_manager = WebSocketManager()