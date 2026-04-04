import os
import sys
import uuid
from pathlib import Path

import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add the api package root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Superuser URL for admin operations (setup/teardown, DDL)
ADMIN_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)

# App user URL for RLS-enforced operations (actual tests)
# This user is created by the migration and is NOT a superuser.
APP_DATABASE_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)

# Ensure asyncpg driver
if ADMIN_DATABASE_URL.startswith("postgresql://"):
    ADMIN_DATABASE_URL = ADMIN_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
if APP_DATABASE_URL.startswith("postgresql://"):
    APP_DATABASE_URL = APP_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Fixed tenant and user IDs for deterministic testing
TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest_asyncio.fixture
async def db_session():
    """
    Provide a per-test database session with seeded data.

    Uses the admin (superuser) connection for setup/teardown (bypass RLS),
    and the app_user connection for the actual test (RLS enforced).
    """
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, poolclass=NullPool)
    app_engine = create_async_engine(APP_DATABASE_URL, poolclass=NullPool)

    try:
        # ── SETUP: seed test data as superuser (bypasses RLS) ──
        async with admin_engine.begin() as conn:
            # Clean up (FK order)
            for table in ["approval_queue", "agent_actions", "notification_log",
                          "amazon_connections", "users"]:
                await conn.execute(
                    text(f"DELETE FROM {table} WHERE tenant_id IN (:a, :b)"),
                    {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
                )
            await conn.execute(
                text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id IN (:a, :b)"),
                {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
            )

            # Seed tenants
            await conn.execute(text(
                "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
                "VALUES (:id, 'Tenant A', 'tenant-a', 'starter', 'active')"),
                {"id": str(TENANT_A_ID)})
            await conn.execute(text(
                "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
                "VALUES (:id, 'Tenant B', 'tenant-b', 'growth', 'active')"),
                {"id": str(TENANT_B_ID)})

            # Seed users
            await conn.execute(text(
                "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                "VALUES (:id, :tid, 'alice@tenant-a.com', 'Alice', 'owner', '$2b$12$hash_a')"),
                {"id": str(USER_A_ID), "tid": str(TENANT_A_ID)})
            await conn.execute(text(
                "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                "VALUES (:id, :tid, 'bob@tenant-b.com', 'Bob', 'owner', '$2b$12$hash_b')"),
                {"id": str(USER_B_ID), "tid": str(TENANT_B_ID)})

            # Clear audit entries from seeding
            await conn.execute(
                text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
            )

        # ── TEST SESSION (as app_user — RLS enforced) ──
        async with AsyncSession(app_engine, expire_on_commit=False) as session:
            yield session

    finally:
        # ── TEARDOWN: clean up as superuser ──
        try:
            async with admin_engine.begin() as conn:
                for table in ["approval_queue", "agent_actions", "notification_log",
                              "amazon_connections", "users"]:
                    await conn.execute(
                        text(f"DELETE FROM {table} WHERE tenant_id IN (:a, :b)"),
                        {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
                    )
                await conn.execute(
                    text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                    {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
                )
                await conn.execute(
                    text("DELETE FROM tenants WHERE id IN (:a, :b)"),
                    {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
                )
        finally:
            await admin_engine.dispose()
            await app_engine.dispose()
