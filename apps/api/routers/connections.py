"""Amazon SP-API OAuth connection endpoints."""

import os
import uuid

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.encryption import encrypt_token
from core.security import decode_token
from integrations.sp_api import MARKETPLACE_MAP, exchange_auth_code

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SP_API_APP_ID = os.getenv("SP_API_CLIENT_ID", "amzn1.application-oa2-client.example")


def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


async def _get_redis():
    return aioredis.from_url(REDIS_URL)


def _extract_tenant_id(authorization: str | None) -> str | None:
    """Extract tenant_id from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
        return payload.get("tenant_id")
    except Exception:
        return None


@router.post("/authorize")
async def authorize(
    body: dict,
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Generate Amazon LWA authorization URL for a marketplace."""
    tenant_id = _extract_tenant_id(authorization)
    if not tenant_id:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    marketplace_id = body.get("marketplace_id")
    if marketplace_id not in MARKETPLACE_MAP:
        return _error("INVALID_MARKETPLACE", f"Unknown marketplace: {marketplace_id}", 400)

    marketplace = MARKETPLACE_MAP[marketplace_id]
    state = str(uuid.uuid4())

    # Store state in Redis for CSRF protection (10 min TTL)
    r = await _get_redis()
    try:
        await r.set(f"oauth_state:{state}", tenant_id, ex=600)
    finally:
        await r.aclose()

    auth_url = (
        f"{marketplace['auth_url']}"
        f"?application_id={SP_API_APP_ID}"
        f"&state={state}"
        f"&version=beta"
    )

    return {"url": auth_url, "state": state}


@router.get("/callback")
async def callback(
    state: str = Query(...),
    spapi_oauth_code: str = Query(default=None),
    selling_partner_id: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Handle Amazon OAuth callback — exchange code for tokens."""
    # Validate state from Redis
    r = await _get_redis()
    try:
        tenant_id = await r.get(f"oauth_state:{state}")
    finally:
        await r.aclose()

    if not tenant_id:
        return _error("INVALID_STATE", "Invalid or expired state token", 400)

    tenant_id = tenant_id.decode() if isinstance(tenant_id, bytes) else tenant_id

    if not spapi_oauth_code:
        return _error("MISSING_CODE", "Missing authorization code", 400)

    # Exchange code for tokens
    try:
        tokens = await exchange_auth_code(spapi_oauth_code)
    except Exception as exc:
        logger.error("oauth_token_exchange_failed", error=str(exc))
        return _error("TOKEN_EXCHANGE_FAILED", "Failed to exchange authorization code", 500)

    refresh_token = tokens.get("refresh_token", "")
    encrypted_refresh = encrypt_token(refresh_token)

    # Set RLS tenant context before writing
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": tenant_id},
    )

    # Store connection
    conn_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO amazon_connections "
            "(id, tenant_id, marketplace_id, seller_id, refresh_token_encrypted, connection_status) "
            "VALUES (:id, :tid, :mid, :sid, :token, 'active')"
        ),
        {
            "id": str(conn_id),
            "tid": tenant_id,
            "mid": "ATVPDKIKX0DER",  # Default US; could be derived from state
            "sid": selling_partner_id or "unknown",
            "token": encrypted_refresh,
        },
    )
    await db.commit()

    # Delete used state
    r = await _get_redis()
    try:
        await r.delete(f"oauth_state:{state}")
    finally:
        await r.aclose()

    return {"success": True, "connection_id": str(conn_id), "seller_id": selling_partner_id}


@router.get("")
async def list_connections(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List Amazon connections for the authenticated tenant."""
    tenant_id = _extract_tenant_id(authorization)
    if not tenant_id:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    result = await db.execute(
        text(
            "SELECT id, marketplace_id, seller_id, connection_status, last_sync_at, created_at "
            "FROM amazon_connections WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    )
    rows = result.fetchall()

    connections = [
        {
            "id": str(r.id),
            "marketplace_id": r.marketplace_id,
            "seller_id": r.seller_id,
            "connection_status": r.connection_status,
            "last_sync_at": r.last_sync_at.isoformat() if r.last_sync_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {"connections": connections}


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Delete an Amazon connection."""
    tenant_id = _extract_tenant_id(authorization)
    if not tenant_id:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    await db.execute(
        text("DELETE FROM amazon_connections WHERE id = :cid AND tenant_id = :tid"),
        {"cid": connection_id, "tid": tenant_id},
    )
    await db.commit()

    return {"success": True}
