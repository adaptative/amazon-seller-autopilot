"""SP-API OAuth connection flow tests — 9 test cases."""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.security import create_access_token

ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def auth_headers_tenant_a():
    token = create_access_token(TENANT_A_ID, USER_A_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_tenant_b():
    token = create_access_token(TENANT_B_ID, USER_B_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def redis_client():
    r = aioredis.from_url(REDIS_URL)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def admin_engine():
    eng = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(admin_engine):
    async with AsyncSession(admin_engine, expire_on_commit=False) as s:
        yield s


@pytest_asyncio.fixture
async def client(admin_engine):
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


@pytest_asyncio.fixture
async def seed_connection_a(admin_engine):
    """Seed an Amazon connection for Tenant A."""
    conn_id = uuid.uuid4()
    async with admin_engine.begin() as conn:
        # Ensure tenant exists
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'OAuth Test A', 'oauth-test-a', 'starter', 'active') "
            "ON CONFLICT (id) DO NOTHING"),
            {"id": str(TENANT_A_ID)})
        # Seed connection
        await conn.execute(text(
            "INSERT INTO amazon_connections (id, tenant_id, marketplace_id, seller_id, connection_status) "
            "VALUES (:id, :tid, 'ATVPDKIKX0DER', 'A3TESTSELLERUS', 'active')"),
            {"id": str(conn_id), "tid": str(TENANT_A_ID)})

    yield {"id": str(conn_id)}

    async with admin_engine.begin() as conn:
        await conn.execute(text("DELETE FROM amazon_connections WHERE tenant_id = :tid"),
                           {"tid": str(TENANT_A_ID)})
        await conn.execute(text("DELETE FROM audit_log WHERE tenant_id = :tid"),
                           {"tid": str(TENANT_A_ID)})


# ── TestOAuthInitiation ───────────────────────────────────────────


class TestOAuthInitiation:

    @pytest.mark.asyncio
    async def test_get_auth_url_returns_amazon_redirect(self, client, auth_headers_tenant_a):
        response = await client.post("/api/v1/connections/authorize", json={
            "marketplace_id": "ATVPDKIKX0DER"
        }, headers=auth_headers_tenant_a)
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()
        assert "url" in data
        assert "sellercentral" in data["url"] or "amazon" in data["url"]
        assert "state" in data

    @pytest.mark.asyncio
    async def test_state_token_stored_in_redis(self, client, auth_headers_tenant_a, redis_client):
        response = await client.post("/api/v1/connections/authorize", json={
            "marketplace_id": "ATVPDKIKX0DER"
        }, headers=auth_headers_tenant_a)
        state = response.json()["state"]
        stored = await redis_client.get(f"oauth_state:{state}")
        assert stored is not None

    @pytest.mark.asyncio
    async def test_rejects_invalid_marketplace(self, client, auth_headers_tenant_a):
        response = await client.post("/api/v1/connections/authorize", json={
            "marketplace_id": "INVALID_MARKET"
        }, headers=auth_headers_tenant_a)
        assert response.status_code == 400


# ── TestOAuthCallback ─────────────────────────────────────────────


class TestOAuthCallback:

    @pytest.mark.asyncio
    @patch("routers.connections.exchange_auth_code", new_callable=AsyncMock)
    async def test_callback_exchanges_code_for_tokens(self, mock_exchange, client, redis_client):
        state = str(uuid.uuid4())
        await redis_client.set(f"oauth_state:{state}", str(TENANT_A_ID), ex=600)

        mock_exchange.return_value = {
            "refresh_token": "Atzr|test_refresh_token",
            "access_token": "Atza|test_access_token",
            "expires_in": 3600,
        }

        response = await client.get(
            f"/api/v1/connections/callback?state={state}&spapi_oauth_code=AUTH_CODE_123&selling_partner_id=A3ROBUSTDATA"
        )
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        mock_exchange.assert_called_once_with("AUTH_CODE_123")

    @pytest.mark.asyncio
    async def test_callback_rejects_invalid_state(self, client):
        response = await client.get(
            "/api/v1/connections/callback?state=invalid-state&spapi_oauth_code=CODE"
        )
        assert response.status_code == 400
        assert "state" in response.json()["error"]["message"].lower()

    @pytest.mark.asyncio
    @patch("routers.connections.exchange_auth_code", new_callable=AsyncMock)
    async def test_tokens_stored_encrypted(self, mock_exchange, client, redis_client, db_session):
        state = str(uuid.uuid4())
        await redis_client.set(f"oauth_state:{state}", str(TENANT_A_ID), ex=600)

        mock_exchange.return_value = {
            "refresh_token": "Atzr|real_token",
            "access_token": "Atza|access",
            "expires_in": 3600,
        }

        await client.get(
            f"/api/v1/connections/callback?state={state}&spapi_oauth_code=CODE&selling_partner_id=A3ENCRYPTED"
        )

        result = await db_session.execute(
            text("SELECT refresh_token_encrypted FROM amazon_connections WHERE seller_id = 'A3ENCRYPTED'")
        )
        row = result.fetchone()
        assert row is not None
        assert row.refresh_token_encrypted != "Atzr|real_token"
        assert len(row.refresh_token_encrypted) > 50

        # Cleanup
        await db_session.execute(text("DELETE FROM amazon_connections WHERE seller_id = 'A3ENCRYPTED'"))
        await db_session.commit()


# ── TestConnectionsList ───────────────────────────────────────────


class TestConnectionsList:

    @pytest.mark.asyncio
    async def test_list_returns_tenant_connections(self, client, auth_headers_tenant_a, seed_connection_a):
        response = await client.get("/api/v1/connections", headers=auth_headers_tenant_a)
        assert response.status_code == 200
        data = response.json()
        assert len(data["connections"]) >= 1
        assert data["connections"][0]["marketplace_id"] == "ATVPDKIKX0DER"

    @pytest.mark.asyncio
    async def test_list_excludes_other_tenant(self, client, auth_headers_tenant_b, seed_connection_a):
        response = await client.get("/api/v1/connections", headers=auth_headers_tenant_b)
        assert response.status_code == 200
        assert len(response.json()["connections"]) == 0

    @pytest.mark.asyncio
    async def test_delete_connection(self, client, auth_headers_tenant_a, seed_connection_a):
        conn_id = seed_connection_a["id"]
        response = await client.delete(f"/api/v1/connections/{conn_id}", headers=auth_headers_tenant_a)
        assert response.status_code == 200
        list_resp = await client.get("/api/v1/connections", headers=auth_headers_tenant_a)
        assert len(list_resp.json()["connections"]) == 0
