"""Approval workflow API endpoints."""

import structlog
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token
from services.workflow_engine import WorkflowEngine

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


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


@router.get("/pending")
async def list_pending(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """List all pending approval actions for the tenant."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    engine = WorkflowEngine(db_session=db)
    actions = await engine.list_pending(tenant_id=auth["tenant_id"])
    return {"actions": actions, "total": len(actions)}


@router.post("/{action_id}/approve")
async def approve_action(
    action_id: str,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Approve a proposed agent action."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    engine = WorkflowEngine(db_session=db)
    try:
        result = await engine.approve(action_id, approved_by=auth["user_id"])
        return {"success": True, **result}
    except Exception as exc:
        return _error("APPROVAL_FAILED", str(exc), 400)


@router.post("/{action_id}/reject")
async def reject_action(
    action_id: str,
    body: dict | None = None,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposed agent action."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    reason = (body or {}).get("reason", "")
    engine = WorkflowEngine(db_session=db)
    try:
        result = await engine.reject(action_id, reason=reason)
        return {"success": True, **result}
    except Exception as exc:
        return _error("REJECTION_FAILED", str(exc), 400)


@router.post("/bulk-approve")
async def bulk_approve(
    body: dict,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Bulk approve actions above a confidence threshold."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    min_confidence = body.get("minConfidence", 0.85)
    engine = WorkflowEngine(db_session=db)
    result = await engine.bulk_approve(
        tenant_id=auth["tenant_id"],
        min_confidence=min_confidence,
        approved_by=auth["user_id"],
    )
    return result
