"""Helper to set the current tenant context for RLS."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """
    Set the current tenant context for Row-Level Security.

    Uses set_config with is_local=true so the setting is automatically
    reset when the current transaction ends. This prevents tenant context
    from leaking across requests in a connection pool.

    Args:
        session: The active SQLAlchemy async session.
        tenant_id: The UUID of the tenant making the request.
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id)},
    )
