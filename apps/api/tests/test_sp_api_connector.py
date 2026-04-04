"""SP-API Connector tests — 14 test cases covering token management,
rate limiting, caching, circuit breaker, and API endpoints."""

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import redis.asyncio as aioredis

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.encryption import encrypt_token
from integrations.sp_api_connector import SPAPIConnector

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TENANT_A_ID = str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
TENANT_B_ID = str(uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))


class MockResponse:
    """Mock httpx response."""

    def __init__(self, status_code: int, json_data: dict | None = None, headers: dict | None = None):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest_asyncio.fixture
async def redis_client():
    r = aioredis.from_url(REDIS_URL)
    yield r
    # Clean up test keys
    async for key in r.scan_iter("sp_api:*"):
        await r.delete(key)
    await r.aclose()


@pytest.fixture
def mock_http():
    return AsyncMock()


@pytest.fixture
def mock_lwa():
    """Mock the LWA token refresh."""
    with patch.object(SPAPIConnector, "_refresh_access_token", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def encrypted_refresh_token():
    return encrypt_token("Atzr|test_refresh_token")


@pytest_asyncio.fixture
async def connector(encrypted_refresh_token, redis_client, mock_http):
    """Connector for Tenant A with mocked HTTP."""
    c = SPAPIConnector(
        tenant_id=TENANT_A_ID,
        refresh_token_encrypted=encrypted_refresh_token,
        redis_client=redis_client,
        http_client=mock_http,
    )
    # Set valid token by default
    c._access_token = "valid_token"
    c._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    # Mock HTTP request method to return listings by default
    mock_http.request = AsyncMock(return_value=MockResponse(200, {"payload": {"items": []}}))
    yield c


@pytest_asyncio.fixture
async def connector_a(encrypted_refresh_token, redis_client):
    mock = AsyncMock()
    mock.request = AsyncMock(return_value=MockResponse(200, {"payload": {"asin": "B08XYZ"}}))
    c = SPAPIConnector(TENANT_A_ID, encrypted_refresh_token, redis_client, http_client=mock)
    c._access_token = "valid"
    c._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    yield c


@pytest_asyncio.fixture
async def connector_b(encrypted_refresh_token, redis_client):
    mock = AsyncMock()
    mock.request = AsyncMock(return_value=MockResponse(200, {"payload": {"asin": "B08XYZ", "price": 999}}))
    c = SPAPIConnector(TENANT_B_ID, encrypted_refresh_token, redis_client, http_client=mock)
    c._access_token = "valid"
    c._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    yield c


# ── TestTokenManagement ───────────────────────────────────────────


class TestTokenManagement:

    @pytest.mark.asyncio
    async def test_auto_refreshes_expired_token(self, connector, mock_lwa, mock_http):
        connector._access_token = "expired_token"
        connector._token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)

        await connector.get_listings("ATVPDKIKX0DER")
        mock_lwa.assert_called_once()

    @pytest.mark.asyncio
    async def test_reuses_valid_token(self, connector, mock_lwa, mock_http):
        connector._access_token = "valid_token"
        connector._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        await connector.get_listings("ATVPDKIKX0DER")
        mock_lwa.assert_not_called()

    @pytest.mark.asyncio
    async def test_refreshes_with_5_min_buffer(self, connector, mock_lwa, mock_http):
        connector._access_token = "almost_expired"
        connector._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=3)

        await connector.get_listings("ATVPDKIKX0DER")
        mock_lwa.assert_called_once()


# ── TestRateLimiting ──────────────────────────────────────────────


class TestRateLimiting:

    @pytest.mark.asyncio
    async def test_respects_sp_api_rate_limits(self, connector, mock_http, redis_client):
        # Disable cache so rate limiter is actually exercised
        connector._redis = None
        call_times = []
        for i in range(10):
            start = time.monotonic()
            await connector.get_listings("ATVPDKIKX0DER")
            call_times.append(time.monotonic() - start)

        total_time = sum(call_times)
        assert total_time > 0.5, f"10 calls took {total_time}s — should be throttled"

    @pytest.mark.asyncio
    async def test_handles_429_with_retry_after(self, connector, mock_http):
        mock_http.request = AsyncMock(side_effect=[
            MockResponse(429, headers={"Retry-After": "0.1", "x-amzn-RateLimit-Limit": "0.5"}),
            MockResponse(200, {"payload": {"items": []}}),
        ])
        await connector.get_listings("ATVPDKIKX0DER")
        assert mock_http.request.call_count == 2


# ── TestCaching ───────────────────────────────────────────────────


class TestCaching:

    @pytest.mark.asyncio
    async def test_caches_catalog_items(self, connector, redis_client, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(200, {
            "payload": {"asin": "B08XYZ", "title": "Test Product"}
        }))

        result1 = await connector.get_catalog_item("B08XYZ")
        result2 = await connector.get_catalog_item("B08XYZ")

        assert mock_http.request.call_count == 1
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_cache_ttl_is_15_minutes(self, connector, redis_client, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(200, {"payload": {"asin": "B08TTL"}}))
        await connector.get_catalog_item("B08TTL")

        # Find the cache key
        keys = []
        async for key in redis_client.scan_iter(f"sp_api:{TENANT_A_ID}:catalog:*"):
            keys.append(key)
        assert len(keys) >= 1
        ttl = await redis_client.ttl(keys[0])
        assert 800 < ttl <= 900

    @pytest.mark.asyncio
    async def test_cache_is_tenant_scoped(self, connector_a, connector_b, redis_client, mock_http):
        await connector_a.get_catalog_item("B08XYZ")
        await connector_b.get_catalog_item("B08XYZ")

        # Each connector has its own mock, so both should have been called
        assert connector_a._http.request.call_count == 1
        assert connector_b._http.request.call_count == 1


# ── TestCircuitBreaker ────────────────────────────────────────────


class TestCircuitBreaker:

    @pytest.mark.asyncio
    async def test_circuit_opens_after_5_failures(self, connector, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(500, {"errors": [{"code": "InternalFailure"}]}))
        # Disable cache and set max_retries=0 to count failures precisely
        connector._redis = None

        for i in range(5):
            with pytest.raises(Exception):
                await connector._request("GET", "/test", "listings", max_retries=0)

        with pytest.raises(Exception, match="circuit.*open|service.*unavailable"):
            await connector._request("GET", "/test", "listings", max_retries=0)
        assert mock_http.request.call_count == 5

    @pytest.mark.asyncio
    async def test_circuit_half_opens_after_timeout(self, connector, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(500))

        for i in range(5):
            with pytest.raises(Exception):
                await connector.get_listings("ATVPDKIKX0DER")

        # Simulate timeout passing
        connector._circuit_breaker._last_failure_time -= 61

        mock_http.request = AsyncMock(return_value=MockResponse(200, {"payload": {"items": []}}))
        result = await connector.get_listings("ATVPDKIKX0DER")
        assert result is not None


# ── TestAPIEndpoints ──────────────────────────────────────────────


class TestAPIEndpoints:

    @pytest.mark.asyncio
    async def test_get_listings_returns_items(self, connector, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(200, {
            "payload": {"items": [
                {"asin": "B08ABC", "title": "Product 1"},
                {"asin": "B08DEF", "title": "Product 2"},
            ]}
        }))
        items = await connector.get_listings("ATVPDKIKX0DER")
        assert len(items) == 2
        assert items[0]["asin"] == "B08ABC"

    @pytest.mark.asyncio
    async def test_get_pricing_returns_offers(self, connector, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(200, {
            "payload": [{"ASIN": "B08ABC", "BuyBoxPrice": {"Amount": 24.99}}]
        }))
        offers = await connector.get_pricing("B08ABC")
        assert offers[0]["BuyBoxPrice"]["Amount"] == 24.99

    @pytest.mark.asyncio
    async def test_get_inventory_returns_supply(self, connector, mock_http):
        mock_http.request = AsyncMock(return_value=MockResponse(200, {
            "payload": {"inventorySummaries": [{"asin": "B08ABC", "totalQuantity": 150}]}
        }))
        inv = await connector.get_inventory("B08ABC")
        assert inv[0]["totalQuantity"] == 150
