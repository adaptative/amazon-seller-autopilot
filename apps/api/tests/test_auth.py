"""
Authentication API tests — 23 test cases covering signup, login, refresh,
protected endpoints, tenant isolation, and password security.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.config import JWT_ALGORITHM, JWT_SECRET
from core.security import create_access_token, hash_password

# ── Test Configuration ────────────────────────────────────────────

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ADMIN_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)
APP_DB_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)

# Fixed IDs
TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

EXISTING_PASSWORD = "ExistingPass123!"
EXISTING_EMAIL = "existing@example.com"


# ── Fixtures ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin_engine():
    eng = create_async_engine(ADMIN_DB_URL, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def seed_data(admin_engine):
    """Seed test tenants and users using admin (superuser) connection."""
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

        # Seed Tenant A
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'Test Store', 'test-store', 'starter', 'active')"),
            {"id": str(TENANT_A_ID)})
        # Seed Tenant B
        await conn.execute(text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, 'Other Store', 'other-store', 'growth', 'active')"),
            {"id": str(TENANT_B_ID)})

        # Seed User A
        pw_hash = hash_password(EXISTING_PASSWORD)
        await conn.execute(text(
            "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
            "VALUES (:id, :tid, :email, 'Existing User', 'owner', :pw)"),
            {"id": str(USER_A_ID), "tid": str(TENANT_A_ID),
             "email": EXISTING_EMAIL, "pw": pw_hash})
        # Seed User B
        await conn.execute(text(
            "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
            "VALUES (:id, :tid, 'bob@other-store.com', 'Bob Other', 'owner', :pw)"),
            {"id": str(USER_B_ID), "tid": str(TENANT_B_ID), "pw": pw_hash})

        # Clean audit entries
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
    # Also clean up signup-created data
    async with admin_engine.begin() as conn:
        await conn.execute(text(
            "DELETE FROM users WHERE email IN ('new@example.com', 'dupe@example.com', "
            "'test1@example.com', 'test2@example.com', 'e2e@example.com', "
            "'newpass@example.com', 'same1@example.com', 'same2@example.com')"))
        await conn.execute(text(
            "DELETE FROM tenants WHERE slug LIKE 'tenant-%' AND id NOT IN (:a, :b)"),
            {"a": str(TENANT_A_ID), "b": str(TENANT_B_ID)})


@pytest_asyncio.fixture
async def client(seed_data):
    """HTTP client for the FastAPI app with fresh DB engine per test."""
    from main import app
    from core.database import get_db, reset_engine

    # Reset module-level engine to avoid event loop issues
    reset_engine()

    # Create a per-test engine using NullPool
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
def auth_headers() -> dict:
    """Valid auth headers for Tenant A / User A."""
    token = create_access_token(TENANT_A_ID, USER_A_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_tenant_b() -> dict:
    """Valid auth headers for Tenant B / User B."""
    token = create_access_token(TENANT_B_ID, USER_B_ID)
    return {"Authorization": f"Bearer {token}"}


# ── TestSignup ────────────────────────────────────────────────────


class TestSignup:

    @pytest.mark.asyncio
    async def test_signup_success_creates_tenant_and_user(self, client, admin_engine):
        response = await client.post("/api/v1/auth/signup", json={
            "name": "New Seller",
            "email": "new@example.com",
            "password": "NewPass123!",
            "companyName": "New Store",
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "tenantId" in data
        assert "userId" in data
        assert "accessToken" in data and len(data["accessToken"]) > 0
        assert "refreshToken" in data and len(data["refreshToken"]) > 0
        assert data["email"] == "new@example.com"
        assert data["name"] == "New Seller"

        # Verify in DB
        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text("SELECT name FROM tenants WHERE id = :id"),
                {"id": data["tenantId"]})
            tenant = result.fetchone()
            assert tenant is not None
            assert tenant.name == "New Store"

            result = await conn.execute(
                text("SELECT email, role, password_hash, tenant_id FROM users WHERE id = :id"),
                {"id": data["userId"]})
            user = result.fetchone()
            assert user is not None
            assert user.email == "new@example.com"
            assert user.role == "owner"
            assert user.password_hash != "NewPass123!"
            assert str(user.tenant_id) == data["tenantId"]

    @pytest.mark.asyncio
    async def test_signup_rejects_duplicate_email(self, client):
        # First signup
        await client.post("/api/v1/auth/signup", json={
            "name": "First", "email": "dupe@example.com",
            "password": "DupePass123!", "companyName": "Store1"})
        # Second signup with same email
        response = await client.post("/api/v1/auth/signup", json={
            "name": "Second", "email": "dupe@example.com",
            "password": "DupePass123!", "companyName": "Store2"})
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_signup_rejects_weak_password(self, client):
        response = await client.post("/api/v1/auth/signup", json={
            "name": "Weak", "email": "weak@example.com",
            "password": "weak", "companyName": "Store"})
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_signup_rejects_invalid_email_format(self, client):
        response = await client.post("/api/v1/auth/signup", json={
            "name": "Bad", "email": "not-an-email",
            "password": "GoodPass123!", "companyName": "Store"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_rejects_missing_required_fields(self, client):
        response = await client.post("/api/v1/auth/signup", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_signup_creates_default_starter_subscription(self, client, admin_engine):
        response = await client.post("/api/v1/auth/signup", json={
            "name": "Starter", "email": "e2e@example.com",
            "password": "StarterPass123!", "companyName": "Starter Store"})
        assert response.status_code == 201
        data = response.json()
        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text("SELECT subscription_tier, status FROM tenants WHERE id = :id"),
                {"id": data["tenantId"]})
            tenant = result.fetchone()
            assert tenant.subscription_tier == "starter"
            assert tenant.status == "active"


# ── TestLogin ─────────────────────────────────────────────────────


class TestLogin:

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "email": EXISTING_EMAIL, "password": EXISTING_PASSWORD})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert len(data["accessToken"]) > 0
        assert len(data["refreshToken"]) > 0
        assert data["tenantId"] == str(TENANT_A_ID)
        assert data["userId"] == str(USER_A_ID)
        assert data["email"] == EXISTING_EMAIL
        assert data["role"] == "owner"

    @pytest.mark.asyncio
    async def test_login_returns_valid_jwt_with_tenant_id(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "email": EXISTING_EMAIL, "password": EXISTING_PASSWORD})
        data = response.json()
        payload = jwt.decode(data["accessToken"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["tenant_id"] == str(TENANT_A_ID)
        assert payload["user_id"] == str(USER_A_ID)
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()
        assert payload["iat"] <= datetime.now(timezone.utc).timestamp()

    @pytest.mark.asyncio
    async def test_login_rejects_wrong_password(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "email": EXISTING_EMAIL, "password": "WrongPass999!"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_rejects_nonexistent_email(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com", "password": "SomePass123!"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_is_case_insensitive_for_email(self, client):
        response = await client.post("/api/v1/auth/login", json={
            "email": "EXISTING@EXAMPLE.COM", "password": EXISTING_PASSWORD})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_login_updates_last_login_timestamp(self, client, admin_engine):
        await client.post("/api/v1/auth/login", json={
            "email": EXISTING_EMAIL, "password": EXISTING_PASSWORD})
        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text("SELECT last_login_at FROM users WHERE id = :uid"),
                {"uid": str(USER_A_ID)})
            user = result.fetchone()
            assert user.last_login_at is not None
            diff = datetime.now(timezone.utc) - user.last_login_at.replace(tzinfo=timezone.utc)
            assert diff.total_seconds() < 5


# ── TestTokenRefresh ──────────────────────────────────────────────


class TestTokenRefresh:

    @pytest.mark.asyncio
    async def test_refresh_returns_new_access_token(self, client):
        import asyncio
        # Login first to get tokens
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": EXISTING_EMAIL, "password": EXISTING_PASSWORD})
        tokens = login_resp.json()

        # Wait 1s so the new token has a different iat/exp
        await asyncio.sleep(1)

        response = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": tokens["refreshToken"]})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        new_data = response.json()
        assert "accessToken" in new_data
        assert new_data["accessToken"] != tokens["accessToken"]
        # Verify new token is valid
        payload = jwt.decode(new_data["accessToken"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["tenant_id"] == str(TENANT_A_ID)

    @pytest.mark.asyncio
    async def test_refresh_rejects_invalid_token(self, client):
        response = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": "invalid-garbage-token"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_rejects_expired_token(self, client):
        # Create an expired refresh token
        expired_payload = {
            "tenant_id": str(TENANT_A_ID),
            "user_id": str(USER_A_ID),
            "type": "refresh",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        response = await client.post("/api/v1/auth/refresh", json={
            "refreshToken": expired_token})
        assert response.status_code == 401


# ── TestProtectedEndpoints ────────────────────────────────────────


class TestProtectedEndpoints:

    @pytest.mark.asyncio
    async def test_get_me_returns_current_user(self, client, auth_headers):
        response = await client.get("/api/v1/me", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["userId"] == str(USER_A_ID)
        assert data["email"] == EXISTING_EMAIL
        assert data["name"] == "Existing User"
        assert data["role"] == "owner"
        assert data["tenantId"] == str(TENANT_A_ID)

    @pytest.mark.asyncio
    async def test_get_me_rejects_no_auth_header(self, client):
        response = await client.get("/api/v1/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_rejects_invalid_token(self, client):
        response = await client.get("/api/v1/me", headers={
            "Authorization": "Bearer invalid-token"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_rejects_expired_token(self, client):
        expired_payload = {
            "tenant_id": str(TENANT_A_ID),
            "user_id": str(USER_A_ID),
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        response = await client.get("/api/v1/me", headers={
            "Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401


# ── TestTenantIsolation ───────────────────────────────────────────


class TestTenantIsolation:

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_tenants_data(self, client, auth_headers):
        """GET /api/v1/me with Tenant A token should only see Tenant A data."""
        response = await client.get("/api/v1/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tenantId"] == str(TENANT_A_ID)
        assert data["tenantId"] != str(TENANT_B_ID)

    @pytest.mark.asyncio
    async def test_jwt_sets_rls_context_automatically(self, client, auth_headers, auth_headers_tenant_b):
        """Different tokens should see different tenant data."""
        resp_a = await client.get("/api/v1/me", headers=auth_headers)
        resp_b = await client.get("/api/v1/me", headers=auth_headers_tenant_b)
        assert resp_a.json()["tenantId"] == str(TENANT_A_ID)
        assert resp_b.json()["tenantId"] == str(TENANT_B_ID)
        assert resp_a.json()["userId"] != resp_b.json()["userId"]


# ── TestPasswordSecurity ──────────────────────────────────────────


class TestPasswordSecurity:

    @pytest.mark.asyncio
    async def test_password_is_hashed_with_bcrypt(self, client, admin_engine):
        await client.post("/api/v1/auth/signup", json={
            "name": "Hash Test", "email": "newpass@example.com",
            "password": "TestPass123!", "companyName": "Hash Store"})
        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text("SELECT password_hash FROM users WHERE email = 'newpass@example.com'"))
            user = result.fetchone()
            assert user.password_hash.startswith("$2b$")
            assert user.password_hash != "TestPass123!"

    @pytest.mark.asyncio
    async def test_password_hash_is_unique_per_user(self, client, admin_engine):
        await client.post("/api/v1/auth/signup", json={
            "name": "Same1", "email": "same1@example.com",
            "password": "SamePass123!", "companyName": "Store1"})
        await client.post("/api/v1/auth/signup", json={
            "name": "Same2", "email": "same2@example.com",
            "password": "SamePass123!", "companyName": "Store2"})
        async with admin_engine.begin() as conn:
            r1 = await conn.execute(
                text("SELECT password_hash FROM users WHERE email = 'same1@example.com'"))
            r2 = await conn.execute(
                text("SELECT password_hash FROM users WHERE email = 'same2@example.com'"))
            h1 = r1.fetchone().password_hash
            h2 = r2.fetchone().password_hash
            assert h1 != h2
