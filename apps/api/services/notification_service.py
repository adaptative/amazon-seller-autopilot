"""Notification service — creates DB records and publishes events."""

import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.event_bus import Event, EventBus, EventType

logger = structlog.get_logger()


class NotificationService:
    """Create notifications in the DB and optionally publish events."""

    def __init__(self, db_session_factory=None, event_bus: EventBus | None = None):
        self._session_factory = db_session_factory
        self._event_bus = event_bus

    async def notify(
        self,
        tenant_id: uuid.UUID,
        type: str,
        title: str,
        body: str,
        severity: str = "info",
        session: AsyncSession | None = None,
    ) -> uuid.UUID:
        """Create a notification record and publish an event."""
        notification_id = uuid.uuid4()

        # Use provided session or create from factory
        if session:
            await self._insert(session, notification_id, tenant_id, type, title, body, severity)
        elif self._session_factory:
            async with self._session_factory() as s:
                await self._insert(s, notification_id, tenant_id, type, title, body, severity)
                await s.commit()
        else:
            raise RuntimeError("No session or session_factory provided")

        # Publish event
        if self._event_bus:
            event = Event(
                type=EventType.NOTIFICATION_CREATED,
                tenant_id=tenant_id,
                payload={
                    "notification_id": str(notification_id),
                    "type": type,
                    "title": title,
                    "severity": severity,
                },
            )
            await self._event_bus.publish(event)

        logger.info("notification_created", notification_id=str(notification_id),
                     tenant_id=str(tenant_id), title=title)
        return notification_id

    async def _insert(
        self, session: AsyncSession, notification_id: uuid.UUID,
        tenant_id: uuid.UUID, type: str, title: str, body: str, severity: str,
    ) -> None:
        await session.execute(
            text(
                "INSERT INTO notification_log (id, tenant_id, type, title, body, severity) "
                "VALUES (:id, :tid, :type, :title, :body, :severity)"
            ),
            {
                "id": str(notification_id),
                "tid": str(tenant_id),
                "type": type,
                "title": title,
                "body": body,
                "severity": severity,
            },
        )

    async def get_unread(
        self, tenant_id: uuid.UUID, limit: int = 20, session: AsyncSession | None = None,
    ) -> list[dict]:
        """Get unread notifications for a tenant."""
        s = session
        if not s and self._session_factory:
            s = self._session_factory()

        await s.execute(
            text("SELECT set_config('app.current_tenant', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        result = await s.execute(
            text("SELECT * FROM notification_log WHERE read = false ORDER BY created_at DESC LIMIT :lim"),
            {"lim": limit},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def mark_read(
        self, tenant_id: uuid.UUID, notification_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Mark a notification as read."""
        s = session
        if not s and self._session_factory:
            s = self._session_factory()

        await s.execute(
            text("SELECT set_config('app.current_tenant', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        await s.execute(
            text("UPDATE notification_log SET read = true WHERE id = :nid"),
            {"nid": str(notification_id)},
        )
        await s.commit()
