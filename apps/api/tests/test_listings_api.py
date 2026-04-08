"""Listing Management API tests — 8 test cases covering paginated listing,
RLS isolation, health score, optimization, apply workflow, and history."""

import json
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.security import create_access_token

# ── Test Configuration ────────────────────────────────────────────

ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TEST_ASIN = "B0TESTLST01"

SAMPLE_LISTING = {
    "title": "Premium Wireless Earbuds with Active Noise Cancellation Bluetooth 5.3",
    "bullet_points": [
        "Active Noise Cancellation — block out background noise for immersive sound",
        "30-Hour Battery Life — extended playtime with compact charging case",
        "Bluetooth 5.3 — stable, low-latency wireless audio connection",
        "IPX5 Waterproof — sweat and splash resistant for workouts",
        "Intuitive Touch Controls — tap to play, pause, skip, or answer calls",
    ],
    "description": "Experience premium audio with our wireless earbuds featuring active noise cancellation.",
    "search_terms": "earphones headphones gym workout commute travel",
}


# ── Fixtures ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_engine():
    eng = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def seed_data(admin_engine):
    """Seed tenants, users, and sample listing agent_actions."""
    async with admin_engine.begin() as conn:
        # Clean up
        for table in ["approval_queue", "agent_actions", "notification_log",
                      "amazon_connections", "users"]:
            await conn.execute(
                text(f"DELETE FROM {table} WHERE tenant_id IN (:a, :b)"),
                {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
            )
        await conn.execute(text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                           {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})
        await conn.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"),
                           {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})

        # Seed tenants
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'Store A', 'store-a', 'starter', 'active')"),
            {"id": str(TENANT_A_ID)})
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'Store B', 'store-b', 'growth', 'active')"),
            {"id": str(TENANT_B_ID)})

        # Seed users
        await conn.execute(text(
            "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
            "VALUES (:id, :tid, 'alice@store-a.com', 'Alice', 'owner', '$2b$12$hash_a')"),
            {"id": str(USER_A_ID), "tid": str(TENANT_A_ID)})
        await conn.execute(text(
            "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
            "VALUES (:id, :tid, 'bob@store-b.com', 'Bob', 'owner', '$2b$12$hash_b')"),
            {"id": str(USER_B_ID), "tid": str(TENANT_B_ID)})

        # Seed a listing agent_action for Tenant A
        await conn.execute(text(
            "INSERT INTO agent_actions "
            "(id, tenant_id, agent_type, action_type, target_asin, status, "
            "proposed_change, reasoning, confidence_score) "
            "VALUES (:id, :tid, 'listing', 'listing_generate', :asin, 'proposed', "
            ":change, 'Test reasoning', 0.88)"),
            {
                "id": str(uuid.uuid4()),
                "tid": str(TENANT_A_ID),
                "asin": TEST_ASIN,
                "change": json.dumps(SAMPLE_LISTING),
            })

        # Seed an Amazon connection for Tenant A
        await conn.execute(text(
            "INSERT INTO amazon_connections "
            "(id, tenant_id, marketplace_id, seller_id, refresh_token_encrypted, connection_status) "
            "VALUES (:id, :tid, 'ATVPDKIKX0DER', 'SELLER001', 'encrypted_token', 'active')"),
            {"id": str(uuid.uuid4()), "tid": str(TENANT_A_ID)})

        # Clean audit entries from seeding
        await conn.execute(text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                           {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})

    yield

    # Teardown
    async with admin_engine.begin() as conn:
        for table in ["approval_queue", "agent_actions", "notification_log",
                      "amazon_connections", "users"]:
            await conn.execute(
                text(f"DELETE FROM {table} WHERE tenant_id IN (:a, :b)"),
                {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)},
            )
        await conn.execute(text("DELETE FROM audit_log WHERE tenant_id IN (:a, :b)"),
                           {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})
        await conn.execute(text("DELETE FROM tenants WHERE id IN (:a, :b)"),
                           {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})


@pytest_asyncio.fixture
async def client(seed_data):
    """HTTP client for the FastAPI app."""
    from main import app
    from core.database import get_db, reset_engine

    reset_engine()
    test_engine = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)

    async def override_get_db():
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
def auth_headers_a() -> dict:
    token = create_access_token(TENANT_A_ID, USER_A_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_b() -> dict:
    token = create_access_token(TENANT_B_ID, USER_B_ID)
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════
#  TEST 1: Paginated listing
# ═══════════════════════════════════════════════════════════════════

class TestListEndpoint:

    @pytest.mark.asyncio
    async def test_list_returns_paginated_listings(self, client, auth_headers_a):
        """GET /api/v1/listings returns items + total for authenticated tenant."""
        resp = await client.get("/api/v1/listings", headers=auth_headers_a)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_respects_rls(self, client, auth_headers_b):
        """Tenant B cannot see Tenant A's listings."""
        resp = await client.get("/api/v1/listings", headers=auth_headers_b)
        assert resp.status_code == 200
        data = resp.json()
        # Tenant B has no listings seeded
        assert data["total"] == 0


# ═══════════════════════════════════════════════════════════════════
#  TEST 2: Detail with health score
# ═══════════════════════════════════════════════════════════════════

class TestDetailEndpoint:

    @pytest.mark.asyncio
    async def test_get_detail_includes_health_score(self, client, auth_headers_a):
        """GET /api/v1/listings/{asin} returns listing with computed healthScore."""
        resp = await client.get(f"/api/v1/listings/{TEST_ASIN}", headers=auth_headers_a)
        assert resp.status_code == 200
        data = resp.json()
        assert "healthScore" in data
        assert isinstance(data["healthScore"], int)
        assert 0 <= data["healthScore"] <= 100
        assert data["asin"] == TEST_ASIN
        assert len(data["bullets"]) == 5


# ═══════════════════════════════════════════════════════════════════
#  TEST 3: Optimize endpoint
# ═══════════════════════════════════════════════════════════════════

class TestOptimizeEndpoint:

    @pytest.mark.asyncio
    async def test_optimize_returns_suggestion_with_diff(self, client, auth_headers_a):
        """POST /api/v1/listings/{asin}/optimize triggers agent, returns suggestion."""
        mock_result = {
            "listing": {
                "title": "Optimized Wireless Earbuds Title",
                "bullet_points": ["B1", "B2", "B3", "B4", "B5"],
                "description": "Optimized description",
                "search_terms": "optimized search terms",
            },
            "diff": {"title": {"old": "old title", "new": "new title"}},
            "reasoning": "Improved keyword density",
            "confidence_score": 0.91,
        }

        with patch("routers.listings.ANTHROPIC_API_KEY", "test-key"), \
             patch("routers.listings.ListingAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.optimize = AsyncMock(return_value=mock_result)
            MockAgent.return_value = mock_instance

            resp = await client.post(
                f"/api/v1/listings/{TEST_ASIN}/optimize",
                headers=auth_headers_a,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "title" in data
        assert "confidence" in data
        assert "diff" in data
        assert data["confidence"] == 0.91

    @pytest.mark.asyncio
    async def test_optimize_requires_active_connection(self, client, auth_headers_b):
        """POST optimize without an active SP-API connection returns 400."""
        resp = await client.post(
            f"/api/v1/listings/{TEST_ASIN}/optimize",
            headers=auth_headers_b,
        )
        assert resp.status_code == 400
        assert "NO_ACTIVE_CONNECTION" in resp.json()["error"]["code"]


# ═══════════════════════════════════════════════════════════════════
#  TEST 4: Apply workflow
# ═══════════════════════════════════════════════════════════════════

class TestApplyEndpoint:

    @pytest.mark.asyncio
    async def test_apply_creates_approved_action(self, client, auth_headers_a, admin_engine):
        """POST /api/v1/listings/{asin}/apply updates action status to approved."""
        resp = await client.post(
            f"/api/v1/listings/{TEST_ASIN}/apply",
            headers=auth_headers_a,
            json={"title": "Applied title"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "action_id" in data

        # Verify in DB that status is now completed (approved then executed)
        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT status, approved_by FROM agent_actions "
                    "WHERE id = :aid AND tenant_id = :tid"
                ),
                {"aid": data["action_id"], "tid": str(TENANT_A_ID)},
            )
            row = result.fetchone()
            assert row is not None
            assert row.status == "completed"
            assert str(row.approved_by) == str(USER_A_ID)

    @pytest.mark.asyncio
    async def test_apply_calls_sp_api_update(self, client, auth_headers_a):
        """POST apply completes the action (simulating SP-API update)."""
        resp = await client.post(
            f"/api/v1/listings/{TEST_ASIN}/apply",
            headers=auth_headers_a,
            json={"title": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ═══════════════════════════════════════════════════════════════════
#  TEST 5: History
# ═══════════════════════════════════════════════════════════════════

class TestHistoryEndpoint:

    @pytest.mark.asyncio
    async def test_history_returns_past_optimizations(self, client, auth_headers_a):
        """GET /api/v1/listings/{asin}/history returns list of past agent actions."""
        resp = await client.get(
            f"/api/v1/listings/{TEST_ASIN}/history",
            headers=auth_headers_a,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "actions" in data
        assert isinstance(data["actions"], list)
        assert len(data["actions"]) >= 1
        action = data["actions"][0]
        assert action["actionType"] == "listing_generate"
        assert "confidenceScore" in action
        assert "reasoning" in action
