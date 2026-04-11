"""Notification API endpoints."""

import structlog
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _extract_auth(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
        return {"tenant_id": payload.get("tenant_id"), "user_id": payload.get("user_id")}
    except Exception:
        return None


@router.get("/unread-count")
async def unread_count(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Return the count of unread notifications for the tenant."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": tenant_id},
    )

    result = await db.execute(
        text("SELECT COUNT(*) FROM notification_log WHERE tenant_id = :tid AND read = false"),
        {"tid": tenant_id},
    )
    count = result.scalar() or 0
    return {"count": count}


@router.get("")
async def list_notifications(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Return notifications for the tenant."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": tenant_id},
    )

    result = await db.execute(text(
        "SELECT id, type, title, body, severity, read, created_at "
        "FROM notification_log WHERE tenant_id = :tid "
        "ORDER BY created_at DESC LIMIT 50"
    ), {"tid": tenant_id})

    notifications = [
        {
            "id": str(r.id),
            "type": r.type,
            "title": r.title,
            "body": r.body,
            "severity": r.severity,
            "read": r.read,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in result.fetchall()
    ]
    return {"notifications": notifications}


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": tenant_id},
    )

    await db.execute(
        text("UPDATE notification_log SET read = true WHERE id = :nid AND tenant_id = :tid"),
        {"nid": notification_id, "tid": tenant_id},
    )
    await db.commit()
    return {"success": True}
