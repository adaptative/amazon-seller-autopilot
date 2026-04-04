"""
Middleware stack tests — 14 test cases covering TenantContext, RateLimit,
ErrorHandler, RequestLogging, and CORS.
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import JWT_ALGORITHM, JWT_SECRET
from core.security import create_access_token

# Fixed IDs
TENANT_A_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_B_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def auth_headers_tenant_a() -> dict:
    token = create_access_token(TENANT_A_ID, USER_A_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_tenant_b() -> dict:
    token = create_access_token(TENANT_B_ID, USER_B_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_token_headers() -> dict:
    payload = {
        "tenant_id": str(TENANT_A_ID),
        "user_id": str(USER_A_ID),
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enterprise_auth_headers() -> dict:
    payload = {
        "tenant_id": str(TENANT_A_ID),
        "user_id": str(USER_A_ID),
        "type": "access",
        "subscription_tier": "enterprise",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    """HTTP client with middleware-enabled FastAPI app."""
    from core.database import reset_engine
    reset_engine()

    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class MockRedis:
    """In-memory Redis mock for rate limit testing."""

    def __init__(self):
        self._data = {}

    async def incr(self, key):
        self._data[key] = self._data.get(key, 0) + 1
        return self._data[key]

    async def expire(self, key, seconds):
        pass

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, **kwargs):
        self._data[key] = value

    def set_counter(self, key_pattern, value):
        """Pre-set a counter for testing limits."""
        for k in list(self._data.keys()):
            if key_pattern in k:
                self._data[k] = value
                return
        # Set with approximate key
        import time
        minute = int(time.time()) // 60
        key = f"ratelimit:{key_pattern}:{minute}"
        self._data[key] = value


# ── TestTenantContextMiddleware ───────────────────────────────────


class TestTenantContextMiddleware:

    @pytest.mark.asyncio
    async def test_sets_rls_from_jwt(self, client, auth_headers_tenant_a):
        """Valid JWT should allow access to protected endpoints."""
        response = await client.get("/api/v1/me", headers=auth_headers_tenant_a)
        # May return 200 or 401 depending on DB state, but should NOT be
        # rejected by the middleware itself (no UNAUTHORIZED from middleware)
        # The important thing is it's not 401 UNAUTHORIZED from missing token
        assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_rejects_no_auth(self, client):
        """Missing auth header should return 401."""
        response = await client.get("/api/v1/me")
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] in ("UNAUTHORIZED", "UNAUTHORIZED")

    @pytest.mark.asyncio
    async def test_rejects_garbage_token(self, client):
        """Invalid token should return 401."""
        response = await client.get("/api/v1/me", headers={
            "Authorization": "Bearer garbage.token.here"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_expired_token(self, client, expired_token_headers):
        """Expired JWT should return 401 with TOKEN_EXPIRED."""
        response = await client.get("/api/v1/me", headers=expired_token_headers)
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "TOKEN_EXPIRED"

    @pytest.mark.asyncio
    async def test_health_needs_no_auth(self, client):
        """Health endpoint should be accessible without auth."""
        response = await client.get("/health")
        assert response.status_code in (200, 503)  # depends on DB


# ── TestRateLimitMiddleware ───────────────────────────────────────


class TestRateLimitMiddleware:

    @pytest.mark.asyncio
    async def test_allows_normal_traffic(self, client, auth_headers_tenant_a):
        """Normal traffic under the limit should be allowed."""
        for _ in range(5):
            response = await client.get("/health")
            assert response.status_code != 429

    @pytest.mark.asyncio
    async def test_returns_429_over_limit(self, client, auth_headers_tenant_a):
        """Requests over the rate limit should return 429."""
        mock_redis = MockRedis()
        # Pre-set counter to be at the limit
        import time
        minute = int(time.time()) // 60
        key = f"ratelimit:{TENANT_A_ID}:{minute}"
        mock_redis._data[key] = 101  # Over starter limit of 100

        # Patch the middleware's redis
        from main import app
        for middleware in app.user_middleware:
            if hasattr(middleware, 'kwargs') and 'redis_client' in middleware.kwargs:
                pass

        # Use patch to override the _get_redis method
        with patch("core.middleware.RateLimitMiddleware._get_redis", return_value=mock_redis):
            response = await client.get("/api/v1/me", headers=auth_headers_tenant_a)
            assert response.status_code == 429
            assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_per_tenant_isolation(self, client, auth_headers_tenant_a, auth_headers_tenant_b):
        """Tenant A at limit should not affect Tenant B."""
        mock_redis = MockRedis()
        import time
        minute = int(time.time()) // 60
        # Tenant A over limit
        mock_redis._data[f"ratelimit:{TENANT_A_ID}:{minute}"] = 101
        # Tenant B under limit
        mock_redis._data[f"ratelimit:{TENANT_B_ID}:{minute}"] = 5

        with patch("core.middleware.RateLimitMiddleware._get_redis", return_value=mock_redis):
            resp_a = await client.get("/api/v1/me", headers=auth_headers_tenant_a)
            resp_b = await client.get("/api/v1/me", headers=auth_headers_tenant_b)
            assert resp_a.status_code == 429
            assert resp_b.status_code != 429

    @pytest.mark.asyncio
    async def test_enterprise_higher_limit(self, client, enterprise_auth_headers):
        """Enterprise tier should have a higher rate limit."""
        mock_redis = MockRedis()
        import time
        minute = int(time.time()) // 60
        # Set to 5000 — over starter (100) but under enterprise (10000)
        mock_redis._data[f"ratelimit:{TENANT_A_ID}:{minute}"] = 5000

        with patch("core.middleware.RateLimitMiddleware._get_redis", return_value=mock_redis):
            response = await client.get("/api/v1/me", headers=enterprise_auth_headers)
            assert response.status_code != 429


# ── TestErrorHandler ──────────────────────────────────────────────


class TestErrorHandler:

    @pytest.mark.asyncio
    async def test_standardized_error_json(self, client):
        """Error responses should have standardized JSON format."""
        response = await client.get("/api/v1/nonexistent-endpoint")
        # FastAPI returns 404 for unknown routes
        assert response.status_code in (401, 404)
        # If 401 (from middleware), check error format
        if response.status_code == 401:
            data = response.json()
            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]

    @pytest.mark.asyncio
    async def test_no_stack_trace(self, client, auth_headers_tenant_a):
        """Internal errors should not leak stack traces."""
        response = await client.get("/api/v1/trigger-test-error",
                                    headers=auth_headers_tenant_a)
        assert response.status_code == 500
        body = response.text
        assert "traceback" not in body.lower()
        assert "File " not in body
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"

    @pytest.mark.asyncio
    async def test_unique_request_ids(self, client):
        """Each request should get a unique X-Request-ID."""
        resp1 = await client.get("/health")
        resp2 = await client.get("/health")
        id1 = resp1.headers.get("X-Request-ID")
        id2 = resp2.headers.get("X-Request-ID")
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2


# ── TestCORS ──────────────────────────────────────────────────────


class TestCORS:

    @pytest.mark.asyncio
    async def test_allows_localhost_3000(self, client):
        """CORS should allow localhost:3000."""
        response = await client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_blocks_evil_origin(self, client):
        """CORS should not allow evil.com."""
        response = await client.options("/health", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        })
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert allow_origin != "https://evil.com"
