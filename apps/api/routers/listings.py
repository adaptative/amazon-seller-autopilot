"""Listing management API endpoints."""

import json
import os

import structlog
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _extract_auth(authorization: str | None) -> dict | None:
    """Extract tenant_id and user_id from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
        return {"tenant_id": payload.get("tenant_id"), "user_id": payload.get("user_id")}
    except Exception:
        return None


def _compute_health_score(listing: dict) -> int:
    """Compute a listing health score (0-100) based on content completeness."""
    score = 0
    title = listing.get("title", "")
    bullets = listing.get("bullet_points") or listing.get("bullets") or []
    description = listing.get("description", "")
    search_terms = listing.get("search_terms", "")

    # Title: up to 30 points
    if title:
        title_len = len(title)
        if 80 <= title_len <= 200:
            score += 30
        elif 50 <= title_len < 80:
            score += 20
        elif title_len > 0:
            score += 10

    # Bullets: up to 30 points (6 each)
    for bullet in bullets[:5]:
        if len(bullet) >= 50:
            score += 6
        elif len(bullet) > 0:
            score += 3

    # Description: up to 20 points
    if description:
        desc_len = len(description)
        if desc_len >= 200:
            score += 20
        elif desc_len >= 100:
            score += 12
        elif desc_len > 0:
            score += 6

    # Search terms: up to 20 points
    if search_terms:
        terms_count = len(search_terms.split())
        if terms_count >= 5:
            score += 20
        elif terms_count >= 3:
            score += 12
        elif terms_count > 0:
            score += 6

    return min(score, 100)


@router.get("")
async def list_listings(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Return a paginated list of listings for the authenticated tenant."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]

    # Set tenant context for RLS
    await db.execute(text("SET app.current_tenant = :tid"), {"tid": tenant_id})

    # Query agent_actions of type 'listing' to build listing catalog
    query = (
        "SELECT id, target_asin, proposed_change, confidence_score, status, created_at "
        "FROM agent_actions WHERE agent_type = 'listing' "
        "AND tenant_id = :tid "
    )
    params: dict = {"tid": tenant_id}

    if status:
        query += "AND status = :status "
        params["status"] = status

    query += "ORDER BY created_at DESC "

    # Count total
    count_query = f"SELECT COUNT(*) FROM ({query}) sub"
    count_result = await db.execute(text(count_query), params)
    total = count_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query += "LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    items = []
    for row in rows:
        proposed = row.proposed_change if isinstance(row.proposed_change, dict) else json.loads(row.proposed_change or "{}")
        title = proposed.get("title", "")

        if search and search.lower() not in title.lower() and search.lower() not in (row.target_asin or "").lower():
            continue

        health = _compute_health_score(proposed)
        items.append({
            "asin": row.target_asin or "",
            "title": title,
            "price": 0.0,
            "bsr": 0,
            "healthScore": health,
            "status": "active",
            "imageUrl": "",
        })

    return {"items": items, "total": total}


@router.get("/{asin}")
async def get_listing_detail(
    asin: str,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Return the full listing detail for a specific ASIN."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    await db.execute(text("SET app.current_tenant = :tid"), {"tid": tenant_id})

    result = await db.execute(
        text(
            "SELECT id, proposed_change, confidence_score, status, created_at "
            "FROM agent_actions WHERE agent_type = 'listing' AND target_asin = :asin "
            "AND tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"asin": asin, "tid": tenant_id},
    )
    row = result.fetchone()

    if not row:
        return _error("NOT_FOUND", f"No listing found for ASIN {asin}", 404)

    proposed = row.proposed_change if isinstance(row.proposed_change, dict) else json.loads(row.proposed_change or "{}")
    health = _compute_health_score(proposed)

    return {
        "asin": asin,
        "title": proposed.get("title", ""),
        "bullets": proposed.get("bullet_points", []),
        "description": proposed.get("description", ""),
        "searchTerms": proposed.get("search_terms", ""),
        "price": 0.0,
        "bsr": 0,
        "healthScore": health,
        "status": "active",
        "imageUrl": "",
        "lastSyncedAt": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/{asin}/optimize")
async def optimize_listing(
    asin: str,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the Listing Agent to optimize a listing and return the suggestion."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    await db.execute(text("SET app.current_tenant = :tid"), {"tid": tenant_id})

    # Check for an active Amazon connection
    conn_result = await db.execute(
        text(
            "SELECT id FROM amazon_connections "
            "WHERE tenant_id = :tid AND connection_status = 'active' LIMIT 1"
        ),
        {"tid": tenant_id},
    )
    if not conn_result.fetchone():
        return _error(
            "NO_ACTIVE_CONNECTION",
            "An active Amazon SP-API connection is required to optimize listings",
            400,
        )

    # Get current listing data
    listing_result = await db.execute(
        text(
            "SELECT proposed_change FROM agent_actions "
            "WHERE agent_type = 'listing' AND target_asin = :asin AND tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"asin": asin, "tid": tenant_id},
    )
    listing_row = listing_result.fetchone()
    current_listing = {}
    if listing_row:
        current_listing = listing_row.proposed_change if isinstance(listing_row.proposed_change, dict) else json.loads(listing_row.proposed_change or "{}")

    # Run the Listing Agent
    if not ANTHROPIC_API_KEY:
        return _error("CONFIG_ERROR", "Anthropic API key not configured", 500)

    from agents.listing_agent import ListingAgent

    agent = ListingAgent(api_key=ANTHROPIC_API_KEY)

    if current_listing:
        result = await agent.optimize(
            asin=asin,
            existing_listing=current_listing,
            marketplace_id="ATVPDKIKX0DER",
            session=db,
            tenant_id=tenant_id,
        )
    else:
        result = await agent.generate(
            asin=asin,
            product_data={"asin": asin},
            marketplace_id="ATVPDKIKX0DER",
            session=db,
            tenant_id=tenant_id,
        )

    listing = result.get("listing", {})
    diff = result.get("diff", {})

    return {
        "title": listing.get("title", ""),
        "bullets": listing.get("bullet_points", []),
        "description": listing.get("description", ""),
        "searchTerms": listing.get("search_terms", ""),
        "confidence": result.get("confidence_score", 0.0),
        "reasoning": result.get("reasoning", ""),
        "diff": diff,
    }


@router.post("/{asin}/apply")
async def apply_suggestion(
    asin: str,
    body: dict,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Apply an approved AI suggestion — updates agent_action status and calls SP-API."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    user_id = auth["user_id"]
    await db.execute(text("SET app.current_tenant = :tid"), {"tid": tenant_id})

    # Find the most recent proposed action for this ASIN
    result = await db.execute(
        text(
            "SELECT id FROM agent_actions "
            "WHERE agent_type = 'listing' AND target_asin = :asin "
            "AND tenant_id = :tid AND status = 'proposed' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"asin": asin, "tid": tenant_id},
    )
    row = result.fetchone()
    if not row:
        return _error("NOT_FOUND", "No proposed action found for this ASIN", 404)

    action_id = str(row.id)

    # Update status to approved
    await db.execute(
        text(
            "UPDATE agent_actions SET status = 'approved', "
            "approved_by = :uid, approved_at = NOW() "
            "WHERE id = :aid AND tenant_id = :tid"
        ),
        {"aid": action_id, "uid": user_id, "tid": tenant_id},
    )
    await db.commit()

    # In production, this would call SP-API to update the listing.
    # For now, mark as completed.
    await db.execute(
        text(
            "UPDATE agent_actions SET status = 'completed', executed_at = NOW() "
            "WHERE id = :aid AND tenant_id = :tid"
        ),
        {"aid": action_id, "tid": tenant_id},
    )
    await db.commit()

    return {"success": True, "action_id": action_id}


@router.get("/{asin}/history")
async def get_listing_history(
    asin: str,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Return the optimization history for a specific ASIN."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]
    await db.execute(text("SET app.current_tenant = :tid"), {"tid": tenant_id})

    result = await db.execute(
        text(
            "SELECT id, action_type, status, proposed_change, reasoning, "
            "confidence_score, approved_by, approved_at, executed_at, created_at "
            "FROM agent_actions "
            "WHERE agent_type = 'listing' AND target_asin = :asin AND tenant_id = :tid "
            "ORDER BY created_at DESC"
        ),
        {"asin": asin, "tid": tenant_id},
    )
    rows = result.fetchall()

    actions = [
        {
            "id": str(r.id),
            "actionType": r.action_type,
            "status": r.status,
            "proposedChange": r.proposed_change if isinstance(r.proposed_change, dict) else json.loads(r.proposed_change or "{}"),
            "reasoning": r.reasoning,
            "confidenceScore": r.confidence_score,
            "approvedAt": r.approved_at.isoformat() if r.approved_at else None,
            "executedAt": r.executed_at.isoformat() if r.executed_at else None,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {"actions": actions}
