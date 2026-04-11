"""Global search API — searches across listings, actions, and notifications."""

import json

import structlog
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/search", tags=["search"])


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


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Search across listings, agent actions, and notifications."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]

    # Set RLS context
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": tenant_id},
    )

    results = []
    search_term = f"%{q}%"

    # Search agent_actions (listings and other actions)
    actions_result = await db.execute(text(
        "SELECT id, agent_type, action_type, target_asin, proposed_change, reasoning "
        "FROM agent_actions WHERE tenant_id = :tid "
        "AND (target_asin ILIKE :q "
        "  OR reasoning ILIKE :q "
        "  OR proposed_change::text ILIKE :q) "
        "ORDER BY created_at DESC LIMIT 10"
    ), {"tid": tenant_id, "q": search_term})

    for row in actions_result.fetchall():
        proposed = row.proposed_change if isinstance(row.proposed_change, dict) else json.loads(row.proposed_change or "{}")
        title = proposed.get("title", row.reasoning or row.action_type or "")
        category = "listings" if row.agent_type == "listing" else "actions"
        results.append({
            "id": str(row.id),
            "category": category,
            "title": title[:100],
            "subtitle": f"ASIN: {row.target_asin}" if row.target_asin else row.agent_type,
        })

    # Search notifications
    notif_result = await db.execute(text(
        "SELECT id, title, body, type FROM notification_log "
        "WHERE tenant_id = :tid AND (title ILIKE :q OR body ILIKE :q) "
        "ORDER BY created_at DESC LIMIT 5"
    ), {"tid": tenant_id, "q": search_term})

    for row in notif_result.fetchall():
        results.append({
            "id": str(row.id),
            "category": "notifications",
            "title": row.title or "",
            "subtitle": row.type or "",
        })

    return {"results": results}
