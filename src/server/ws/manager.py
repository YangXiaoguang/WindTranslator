"""WebSocket connection manager for real-time progress updates."""

from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by task/room id."""

    def __init__(self) -> None:
        self._rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        """Accept a WebSocket and add it to a room."""
        await ws.accept()
        self._rooms[room_id].append(ws)
        log.debug("WS connected: room=%s, total=%d", room_id, len(self._rooms[room_id]))

    def disconnect(self, room_id: str, ws: WebSocket) -> None:
        """Remove a WebSocket from a room."""
        conns = self._rooms.get(room_id)
        if conns and ws in conns:
            conns.remove(ws)
            if not conns:
                del self._rooms[room_id]

    async def broadcast(self, room_id: str, data: dict) -> None:
        """Send a JSON message to all connections in a room."""
        conns = self._rooms.get(room_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(room_id, ws)
