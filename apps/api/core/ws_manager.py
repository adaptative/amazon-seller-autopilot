"""WebSocket connection manager with per-tenant routing."""

from collections import defaultdict

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections grouped by tenant_id."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, tenant_id: str) -> None:
        await websocket.accept()
        self._connections[tenant_id].append(websocket)
        logger.info("ws_connected", tenant_id=tenant_id)

    def disconnect(self, websocket: WebSocket, tenant_id: str) -> None:
        if tenant_id in self._connections:
            self._connections[tenant_id] = [
                ws for ws in self._connections[tenant_id] if ws != websocket
            ]
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]
        logger.info("ws_disconnected", tenant_id=tenant_id)

    async def send_to_tenant(self, tenant_id: str, message: dict) -> None:
        """Send a message to all connections for a specific tenant."""
        connections = self._connections.get(tenant_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, tenant_id)

    async def publish_to_tenant(
        self, tenant_id: str, event_type: str, data: dict
    ) -> None:
        """Publish an event to all WebSocket connections for a tenant."""
        await self.send_to_tenant(tenant_id, {"type": event_type, "data": data})

    async def broadcast_all(self, message: dict) -> None:
        """Broadcast to ALL connected clients."""
        for tenant_id in list(self._connections.keys()):
            await self.send_to_tenant(tenant_id, message)


# Global instance
manager = ConnectionManager()
