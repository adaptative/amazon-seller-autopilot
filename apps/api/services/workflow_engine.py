"""Human Approval Workflow Engine — state machine for agent action approvals."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.event_bus import Event, EventBus, EventType

logger = structlog.get_logger()

# Valid state transitions
VALID_TRANSITIONS = {
    "proposed": {"executing", "rejected"},
    "executing": {"completed", "failed"},
    "approved": {"executing"},
}

AUTO_APPROVE_CONFIDENCE_THRESHOLD = 0.95


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class WorkflowEngine:
    """State machine for agent action approval workflow.

    Manages the lifecycle: proposed -> executing -> completed/failed
    with optional auto-approval for high-confidence actions.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        event_bus: EventBus | None = None,
        agent_registry: dict | None = None,
    ):
        self.db = db_session
        self.event_bus = event_bus
        self.agents = agent_registry or {}

    async def _get_action(self, action_id: str) -> dict:
        """Fetch an agent_action by ID."""
        result = await self.db.execute(
            text(
                "SELECT id, tenant_id, agent_type, action_type, target_asin, "
                "status, proposed_change, reasoning, confidence_score "
                "FROM agent_actions WHERE id = :id"
            ),
            {"id": str(action_id)},
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"Action {action_id} not found")
        return {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "agent_type": row.agent_type,
            "action_type": row.action_type,
            "target_asin": row.target_asin,
            "status": row.status,
            "proposed_change": row.proposed_change if isinstance(row.proposed_change, dict) else json.loads(row.proposed_change or "{}"),
            "reasoning": row.reasoning,
            "confidence_score": row.confidence_score,
        }

    async def _update_status(self, action_id: str, new_status: str, **kwargs) -> None:
        """Update the status of an agent_action with optional extra fields."""
        set_parts = ["status = :status"]
        params: dict = {"id": str(action_id), "status": new_status}

        if "approved_by" in kwargs:
            set_parts.append("approved_by = :approved_by")
            params["approved_by"] = str(kwargs["approved_by"])
        if "approved_at" in kwargs:
            set_parts.append("approved_at = :approved_at")
            params["approved_at"] = kwargs["approved_at"]
        if "executed_at" in kwargs:
            set_parts.append("executed_at = :executed_at")
            params["executed_at"] = kwargs["executed_at"]
        if "result" in kwargs:
            set_parts.append("result = :result")
            params["result"] = json.dumps(kwargs["result"])

        query = f"UPDATE agent_actions SET {', '.join(set_parts)} WHERE id = :id"
        await self.db.execute(text(query), params)
        await self.db.commit()

    def _validate_transition(self, current_status: str, target_status: str) -> None:
        """Validate that a state transition is allowed."""
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition: cannot move from '{current_status}' to '{target_status}'"
            )

    async def approve(self, action_id: str, approved_by: uuid.UUID | str | None = None) -> dict:
        """Approve a proposed action, transition to executing, and trigger execution."""
        action = await self._get_action(str(action_id))
        self._validate_transition(action["status"], "executing")

        now = datetime.now(timezone.utc)
        update_kwargs: dict = {"approved_at": now}
        if approved_by is not None:
            update_kwargs["approved_by"] = approved_by
        await self._update_status(
            str(action_id),
            "executing",
            **update_kwargs,
        )

        # Publish event
        if self.event_bus:
            event = Event(
                type=EventType.AGENT_ACTION_APPROVED,
                tenant_id=uuid.UUID(action["tenant_id"]),
                payload={
                    "action_id": str(action_id),
                    "agent_type": action["agent_type"],
                    "target_asin": action["target_asin"],
                },
            )
            try:
                await self.event_bus.publish(event)
            except Exception:
                logger.warning("event_publish_failed", action_id=str(action_id))

        # Execute via agent
        agent = self.agents.get(action["agent_type"])
        if agent and hasattr(agent, "execute"):
            try:
                exec_result = await agent.execute(action)
                await self._update_status(
                    str(action_id),
                    "completed",
                    executed_at=datetime.now(timezone.utc),
                    result=exec_result,
                )
                return {"status": "completed", "result": exec_result}
            except Exception as exc:
                await self._update_status(
                    str(action_id),
                    "failed",
                    executed_at=datetime.now(timezone.utc),
                    result={"error": str(exc)},
                )
                return {"status": "failed", "error": str(exc)}

        return {"status": "executing", "action_id": str(action_id)}

    async def reject(self, action_id: str, reason: str = "") -> dict:
        """Reject a proposed action."""
        action = await self._get_action(str(action_id))
        self._validate_transition(action["status"], "rejected")

        await self._update_status(str(action_id), "rejected")

        # Store rejection reason in result field
        if reason:
            await self.db.execute(
                text("UPDATE agent_actions SET result = :result WHERE id = :id"),
                {"id": str(action_id), "result": json.dumps({"rejection_reason": reason})},
            )
            await self.db.commit()

        # Publish event
        if self.event_bus:
            event = Event(
                type=EventType.AGENT_ACTION_REJECTED,
                tenant_id=uuid.UUID(action["tenant_id"]),
                payload={"action_id": str(action_id), "reason": reason},
            )
            try:
                await self.event_bus.publish(event)
            except Exception:
                logger.warning("event_publish_failed", action_id=str(action_id))

        return {"status": "rejected", "reason": reason}

    async def create_proposal(
        self,
        tenant_id: str | uuid.UUID,
        agent_type: str,
        action_type: str,
        proposed_change: dict,
        confidence: float,
        target_asin: str | None = None,
        reasoning: str = "",
        auto_approve_eligible: bool = False,
        expires_in_minutes: int | None = None,
    ) -> str:
        """Create a new agent_action proposal and optionally auto-approve."""
        action_id = str(uuid.uuid4())
        tenant_id_str = str(tenant_id)

        await self.db.execute(
            text(
                "INSERT INTO agent_actions "
                "(id, tenant_id, agent_type, action_type, target_asin, status, "
                "proposed_change, reasoning, confidence_score) "
                "VALUES (:id, :tid, :agent_type, :action_type, :asin, 'proposed', "
                ":change, :reasoning, :confidence)"
            ),
            {
                "id": action_id,
                "tid": tenant_id_str,
                "agent_type": agent_type,
                "action_type": action_type,
                "asin": target_asin,
                "change": json.dumps(proposed_change),
                "reasoning": reasoning,
                "confidence": confidence,
            },
        )
        await self.db.commit()

        # Create approval queue item
        expires_at = None
        if expires_in_minutes is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)

        queue_id = str(uuid.uuid4())
        priority = "high" if confidence >= 0.85 else "medium" if confidence >= 0.70 else "low"
        await self.db.execute(
            text(
                "INSERT INTO approval_queue "
                "(id, tenant_id, agent_action_id, priority, auto_approve_eligible, expires_at) "
                "VALUES (:id, :tid, :aid, :priority, :auto_approve, :expires)"
            ),
            {
                "id": queue_id,
                "tid": tenant_id_str,
                "aid": action_id,
                "priority": priority,
                "auto_approve": auto_approve_eligible,
                "expires": expires_at,
            },
        )
        await self.db.commit()

        # Auto-approve if eligible and high confidence
        if auto_approve_eligible and confidence >= AUTO_APPROVE_CONFIDENCE_THRESHOLD:
            await self.approve(action_id, approved_by=None)

        return action_id

    async def bulk_approve(
        self,
        tenant_id: str | uuid.UUID,
        min_confidence: float,
        approved_by: uuid.UUID | str | None = None,
    ) -> dict:
        """Bulk approve all proposed actions above a confidence threshold."""
        tenant_id_str = str(tenant_id)
        result = await self.db.execute(
            text(
                "SELECT id FROM agent_actions "
                "WHERE tenant_id = :tid AND status = 'proposed' "
                "AND confidence_score >= :min_conf"
            ),
            {"tid": tenant_id_str, "min_conf": min_confidence},
        )
        rows = result.fetchall()

        approved_count = 0
        for row in rows:
            try:
                await self.approve(str(row.id), approved_by=approved_by)
                approved_count += 1
            except (InvalidTransitionError, Exception) as exc:
                logger.warning("bulk_approve_skip", action_id=str(row.id), error=str(exc))

        return {"approved_count": approved_count}

    async def list_pending(self, tenant_id: str | uuid.UUID) -> list[dict]:
        """List all pending (proposed) actions for a tenant."""
        tenant_id_str = str(tenant_id)
        result = await self.db.execute(
            text(
                "SELECT a.id, a.agent_type, a.action_type, a.target_asin, "
                "a.status, a.proposed_change, a.reasoning, a.confidence_score, "
                "a.created_at, q.priority, q.expires_at "
                "FROM agent_actions a "
                "LEFT JOIN approval_queue q ON q.agent_action_id = a.id "
                "WHERE a.tenant_id = :tid AND a.status = 'proposed' "
                "ORDER BY CASE q.priority "
                "  WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
                "  WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, "
                "a.created_at DESC"
            ),
            {"tid": tenant_id_str},
        )
        rows = result.fetchall()

        return [
            {
                "id": str(r.id),
                "agentType": r.agent_type,
                "actionType": r.action_type,
                "targetAsin": r.target_asin,
                "status": r.status,
                "proposedChange": r.proposed_change if isinstance(r.proposed_change, dict) else json.loads(r.proposed_change or "{}"),
                "reasoning": r.reasoning,
                "confidenceScore": r.confidence_score,
                "priority": r.priority or "medium",
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                "expiresAt": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rows
        ]

    async def cleanup_expired(self) -> int:
        """Reject all expired proposed actions. Returns count of rejected."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            text(
                "SELECT a.id FROM agent_actions a "
                "JOIN approval_queue q ON q.agent_action_id = a.id "
                "WHERE a.status = 'proposed' AND q.expires_at IS NOT NULL "
                "AND q.expires_at <= :now"
            ),
            {"now": now},
        )
        rows = result.fetchall()

        count = 0
        for row in rows:
            try:
                await self.reject(str(row.id), reason="Expired — auto-rejected")
                count += 1
            except Exception as exc:
                logger.warning("cleanup_expired_failed", action_id=str(row.id), error=str(exc))

        return count
