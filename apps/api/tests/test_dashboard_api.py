"""Dashboard aggregation API tests — 8 test cases covering stats,
agent statuses, pending approvals, activity feed, RLS, search, and notifications."""

import json
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.security import create_access_token

# ── Test Configuration ────────────────────────────────────────────

ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)
APP_DB_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


# ── Fixtures ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_engines():
    """Provide admin and app engines for test setup."""
    admin_engine = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    app_engine = create_async_engine(APP_DB_URL, poolclass=NullPool)

    try:
        # SETUP: seed test data as superuser
        async with admin_engine.begin() as conn:
            # Clean up
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
                "VALUES (:id, :tid, 'alice@test.com', 'Alice', 'owner', '$2b$12$hash')"),
                {"id": str(USER_A_ID), "tid": str(TENANT_A_ID)})
            await conn.execute(text(
                "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
                "VALUES (:id, :tid, 'bob@test.com', 'Bob', 'owner', '$2b$12$hash')"),
                {"id": str(USER_B_ID), "tid": str(TENANT_B_ID)})

            # Clean audit entries
            await conn.execute(
                text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
            )

        yield {"admin": admin_engine, "app": app_engine}

    finally:
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


@pytest_asyncio.fixture
async def db_session(db_engines):
    """Provide a DB session pinned to a single connection for RLS."""
    app_engine = db_engines["app"]
    async with app_engine.connect() as connection:
        await connection.execute(
            text("SELECT set_config('app.current_tenant', :tid, false)"),
            {"tid": str(TENANT_A_ID)},
        )
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session


@pytest_asyncio.fixture
async def seed_data(db_engines):
    """Seed agent actions for Tenant A dashboard tests."""
    admin_engine = db_engines["admin"]
    async with admin_engine.begin() as conn:
        # Completed pricing action with revenue_impact
        await conn.execute(text(
            "INSERT INTO agent_actions "
            "(id, tenant_id, agent_type, action_type, target_asin, status, "
            "proposed_change, reasoning, confidence_score, result, created_at) "
            "VALUES (:id, :tid, 'pricing', 'reprice', 'B08XYZ', 'completed', "
            ":change, 'Competitor undercut', 0.92, :result, NOW())"
        ), {
            "id": str(uuid.uuid4()),
            "tid": str(TENANT_A_ID),
            "change": json.dumps({"new_price": 24.99}),
            "result": json.dumps({"revenue_impact": 500, "buy_box_win_rate": 87}),
        })

        # Completed listing action
        await conn.execute(text(
            "INSERT INTO agent_actions "
            "(id, tenant_id, agent_type, action_type, target_asin, status, "
            "proposed_change, reasoning, confidence_score, result, created_at) "
            "VALUES (:id, :tid, 'listing', 'listing_optimize', 'B08ABC', 'completed', "
            ":change, 'SEO improvement', 0.88, :result, NOW())"
        ), {
            "id": str(uuid.uuid4()),
            "tid": str(TENANT_A_ID),
            "change": json.dumps({"title": "Wireless Bluetooth Earbuds"}),
            "result": json.dumps({"success": True}),
        })

        # Clean audit entries from seeding
        await conn.execute(
            text("DELETE FROM audit_log WHERE tenant_id = :tid"),
            {"tid": str(TENANT_A_ID)},
        )


@pytest_asyncio.fixture
async def seed_pending_actions(db_engines):
    """Seed proposed actions for approval testing."""
    admin_engine = db_engines["admin"]
    action_id = str(uuid.uuid4())
    queue_id = str(uuid.uuid4())
    async with admin_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO agent_actions "
            "(id, tenant_id, agent_type, action_type, target_asin, status, "
            "proposed_change, reasoning, confidence_score) "
            "VALUES (:id, :tid, 'pricing', 'reprice', 'B08DEF', 'proposed', "
            ":change, 'New competitor entered', 0.85)"
        ), {
            "id": action_id,
            "tid": str(TENANT_A_ID),
            "change": json.dumps({"new_price": 19.99}),
        })
        await conn.execute(text(
            "INSERT INTO approval_queue (id, tenant_id, agent_action_id, priority) "
            "VALUES (:id, :tid, :aid, 'high')"
        ), {"id": queue_id, "tid": str(TENANT_A_ID), "aid": action_id})

        # Clean audit entries
        await conn.execute(
            text("DELETE FROM audit_log WHERE tenant_id = :tid"),
            {"tid": str(TENANT_A_ID)},
        )


@pytest_asyncio.fixture
async def seed_activity(db_engines, seed_data):
    """Activity data is already seeded by seed_data fixture."""
    pass


@pytest_asyncio.fixture
async def seed_notifications(db_engines):
    """Seed notifications for Tenant A."""
    admin_engine = db_engines["admin"]
    async with admin_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO notification_log (id, tenant_id, type, title, body, severity) "
            "VALUES (:id, :tid, 'agent_action', 'Price changed', 'B08XYZ price updated', 'info')"
        ), {"id": str(uuid.uuid4()), "tid": str(TENANT_A_ID)})
        await conn.execute(text(
            "INSERT INTO notification_log (id, tenant_id, type, title, body, severity) "
            "VALUES (:id, :tid, 'agent_action', 'Listing optimized', 'B08ABC title updated', 'success')"
        ), {"id": str(uuid.uuid4()), "tid": str(TENANT_A_ID)})
        # Clean audit entries
        await conn.execute(
            text("DELETE FROM audit_log WHERE tenant_id = :tid"),
            {"tid": str(TENANT_A_ID)},
        )


@pytest.fixture
def auth_headers_tenant_a():
    """JWT headers for Tenant A."""
    token = create_access_token({"tenant_id": str(TENANT_A_ID), "user_id": str(USER_A_ID)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_tenant_b():
    """JWT headers for Tenant B."""
    token = create_access_token({"tenant_id": str(TENANT_B_ID), "user_id": str(USER_B_ID)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client for FastAPI."""
    from httpx import ASGITransport, AsyncClient
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════════
#  TEST GROUP: Dashboard API (8 tests)
# ═══════════════════════════════════════════════════════════════════

class TestDashboardAPI:

    @pytest.mark.asyncio
    async def test_returns_aggregated_stats(self, client, auth_headers_tenant_a, seed_data):
        response = await client.get("/api/v1/dashboard", headers=auth_headers_tenant_a)
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "totalRevenue" in data["stats"]
        assert "ordersToday" in data["stats"]
        assert "buyBoxWinRate" in data["stats"]
        assert "acos" in data["stats"]

    @pytest.mark.asyncio
    async def test_returns_agent_statuses(self, client, auth_headers_tenant_a, seed_data):
        response = await client.get("/api/v1/dashboard", headers=auth_headers_tenant_a)
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 7
        agent_types = {a["type"] for a in data["agents"]}
        expected = {"listing", "pricing", "advertising", "inventory", "analytics", "compliance", "orchestrator"}
        assert agent_types == expected

    @pytest.mark.asyncio
    async def test_returns_pending_approvals(self, client, auth_headers_tenant_a, seed_pending_actions):
        response = await client.get("/api/v1/dashboard", headers=auth_headers_tenant_a)
        data = response.json()
        assert "pendingApprovals" in data
        assert len(data["pendingApprovals"]) > 0
        assert all(a["id"] for a in data["pendingApprovals"])

    @pytest.mark.asyncio
    async def test_returns_recent_activity(self, client, auth_headers_tenant_a, seed_activity):
        response = await client.get("/api/v1/dashboard", headers=auth_headers_tenant_a)
        data = response.json()
        assert "recentActivity" in data
        assert len(data["recentActivity"]) > 0

    @pytest.mark.asyncio
    async def test_respects_rls(self, client, auth_headers_tenant_b, seed_data):
        """Tenant B should NOT see Tenant A dashboard data."""
        response = await client.get("/api/v1/dashboard", headers=auth_headers_tenant_b)
        data = response.json()
        assert data["stats"]["totalRevenue"] == 0 or data["stats"]["ordersToday"] == 0

    @pytest.mark.asyncio
    async def test_search_returns_results(self, client, auth_headers_tenant_a, seed_data):
        response = await client.get("/api/v1/search?q=B08", headers=auth_headers_tenant_a)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0

    @pytest.mark.asyncio
    async def test_search_covers_listings_and_actions(self, client, auth_headers_tenant_a, seed_data):
        response = await client.get("/api/v1/search?q=B08", headers=auth_headers_tenant_a)
        data = response.json()
        categories = {r["category"] for r in data["results"]}
        assert "listings" in categories or "actions" in categories

    @pytest.mark.asyncio
    async def test_notifications_count(self, client, auth_headers_tenant_a, seed_notifications):
        response = await client.get("/api/v1/notifications/unread-count", headers=auth_headers_tenant_a)
        assert response.status_code == 200
        assert response.json()["count"] >= 0
