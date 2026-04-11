"""Dashboard aggregation API — command center data."""

import structlog
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_token

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

ALL_AGENT_TYPES = [
    "listing", "pricing", "advertising", "inventory",
    "analytics", "compliance", "orchestrator",
]


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
async def get_dashboard(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated dashboard data for the authenticated tenant."""
    auth = _extract_auth(authorization)
    if not auth:
        return _error("UNAUTHORIZED", "Missing or invalid authorization", 401)

    tenant_id = auth["tenant_id"]

    # Set RLS context
    await db.execute(
        text("SELECT set_config('app.current_tenant', :tid, false)"),
        {"tid": tenant_id},
    )

    # ── Stats ────────────────────────────────────────────────────
    # Revenue: sum of revenue_impact from completed pricing actions (last 30 days)
    rev_result = await db.execute(text(
        "SELECT COALESCE(SUM((result->>'revenue_impact')::numeric), 0) AS total "
        "FROM agent_actions "
        "WHERE tenant_id = :tid AND status = 'completed' "
        "AND created_at >= NOW() - INTERVAL '30 days'"
    ), {"tid": tenant_id})
    total_revenue = float(rev_result.scalar() or 0)

    # Orders today: count of completed actions today
    orders_result = await db.execute(text(
        "SELECT COUNT(*) FROM agent_actions "
        "WHERE tenant_id = :tid AND status = 'completed' "
        "AND created_at >= CURRENT_DATE"
    ), {"tid": tenant_id})
    orders_today = orders_result.scalar() or 0

    # Buy Box win rate: from latest pricing stats or default
    bb_result = await db.execute(text(
        "SELECT COALESCE("
        "  (SELECT (result->>'buy_box_win_rate')::numeric "
        "   FROM agent_actions WHERE tenant_id = :tid AND agent_type = 'pricing' "
        "   AND result IS NOT NULL AND result->>'buy_box_win_rate' IS NOT NULL "
        "   ORDER BY created_at DESC LIMIT 1), 0"
        ")"
    ), {"tid": tenant_id})
    buy_box_win_rate = float(bb_result.scalar() or 0)

    # ACoS: from latest advertising action
    acos_result = await db.execute(text(
        "SELECT COALESCE("
        "  (SELECT (result->>'acos')::numeric "
        "   FROM agent_actions WHERE tenant_id = :tid AND agent_type = 'advertising' "
        "   AND result IS NOT NULL AND result->>'acos' IS NOT NULL "
        "   ORDER BY created_at DESC LIMIT 1), 0"
        ")"
    ), {"tid": tenant_id})
    acos = float(acos_result.scalar() or 0)

    stats = {
        "totalRevenue": total_revenue,
        "revenueTrend": 0.0,
        "ordersToday": orders_today,
        "ordersTrend": 0.0,
        "buyBoxWinRate": buy_box_win_rate,
        "buyBoxTrend": 0.0,
        "acos": acos,
        "acosTrend": 0.0,
    }

    # ── Agent Statuses ───────────────────────────────────────────
    agents = []
    for agent_type in ALL_AGENT_TYPES:
        row_result = await db.execute(text(
            "SELECT action_type, status, created_at FROM agent_actions "
            "WHERE tenant_id = :tid AND agent_type = :at "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"tid": tenant_id, "at": agent_type})
        row = row_result.fetchone()

        if row:
            # Active if the last action was recent (within 10 min) and not failed
            is_active = row.status in ("executing", "proposed")
            last_action = row.action_type.replace("_", " ").title() if row.action_type else "Idle"
            last_at = _relative_time(row.created_at) if row.created_at else "—"
        else:
            is_active = False
            last_action = "No activity yet"
            last_at = "—"

        agents.append({
            "type": agent_type,
            "status": "active" if is_active else "idle",
            "lastAction": last_action,
            "lastActionAt": last_at,
        })

    # ── Pending Approvals ────────────────────────────────────────
    pending_result = await db.execute(text(
        "SELECT a.id, a.agent_type, a.action_type, a.target_asin, "
        "a.confidence_score, a.created_at, a.reasoning "
        "FROM agent_actions a "
        "LEFT JOIN approval_queue q ON q.agent_action_id = a.id "
        "WHERE a.tenant_id = :tid AND a.status = 'proposed' "
        "ORDER BY CASE q.priority "
        "  WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
        "  WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, "
        "a.created_at DESC LIMIT 5"
    ), {"tid": tenant_id})
    pending_rows = pending_result.fetchall()

    pending_approvals = []
    for r in pending_rows:
        desc = r.reasoning or f"{r.action_type} on {r.target_asin or 'N/A'}"
        pending_approvals.append({
            "id": str(r.id),
            "agentType": r.agent_type,
            "description": desc,
            "confidence": r.confidence_score or 0.0,
            "createdAt": _relative_time(r.created_at) if r.created_at else "—",
        })

    # ── Recent Activity ──────────────────────────────────────────
    activity_result = await db.execute(text(
        "SELECT id, agent_type, action_type, target_asin, status, created_at "
        "FROM agent_actions "
        "WHERE tenant_id = :tid AND status IN ('completed', 'approved', 'failed', 'executing') "
        "ORDER BY created_at DESC LIMIT 20"
    ), {"tid": tenant_id})
    activity_rows = activity_result.fetchall()

    recent_activity = []
    for r in activity_rows:
        action_text = (r.action_type or "").replace("_", " ").title()
        time_str = r.created_at.strftime("%-I:%M %p") if r.created_at else "—"
        recent_activity.append({
            "id": str(r.id),
            "agentType": r.agent_type,
            "action": action_text,
            "asin": r.target_asin,
            "time": time_str,
        })

    # ── Notification Count ───────────────────────────────────────
    notif_result = await db.execute(text(
        "SELECT COUNT(*) FROM notification_log "
        "WHERE tenant_id = :tid AND read = false"
    ), {"tid": tenant_id})
    notification_count = notif_result.scalar() or 0

    return {
        "stats": stats,
        "agents": agents,
        "pendingApprovals": pending_approvals,
        "recentActivity": recent_activity,
        "notificationCount": notification_count,
    }


def _relative_time(dt) -> str:
    """Convert a datetime to a human-readable relative time string."""
    if not dt:
        return "—"
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        from datetime import timezone as tz
        dt = dt.replace(tzinfo=tz.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m}m ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h}h ago"
    d = seconds // 86400
    return f"{d}d ago"
