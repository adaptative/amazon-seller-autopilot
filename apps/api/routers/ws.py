"""WebSocket endpoint with JWT authentication and tenant isolation."""

import jwt
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from core.config import JWT_ALGORITHM, JWT_SECRET
from core.ws_manager import manager

logger = structlog.get_logger()

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=None),
):
    """WebSocket endpoint. Connect with ?token=<jwt>."""
    # Validate token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
        return
    except jwt.PyJWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    tenant_id = payload.get("tenant_id")
    user_id = payload.get("user_id")

    if not tenant_id or not user_id:
        await websocket.close(code=4001, reason="Invalid token claims")
        return

    # Accept and track connection
    await manager.connect(websocket, tenant_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "tenant_id": tenant_id,
            "user_id": user_id,
        })

        # Listen for messages
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                logger.debug("ws_message_received", tenant_id=tenant_id, data=data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
    except Exception:
        manager.disconnect(websocket, tenant_id)
