"""Amazon SP-API connector with token management, rate limiting, caching, and circuit breaker."""

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
import structlog

from core.encryption import decrypt_token
from integrations.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

logger = structlog.get_logger()

SP_API_CLIENT_ID = os.getenv("SP_API_CLIENT_ID", "")
SP_API_CLIENT_SECRET = os.getenv("SP_API_CLIENT_SECRET", "")
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

REGION_ENDPOINTS = {
    "na": "https://sellingpartnerapi-na.amazon.com",
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}

SANDBOX_ENDPOINT = "https://sandbox.sellingpartnerapi-na.amazon.com"

# Cache TTLs in seconds
CACHE_TTLS = {
    "catalog": 900,     # 15 min
    "pricing": 300,     # 5 min
    "inventory": 60,    # 1 min
    "listings": 300,    # 5 min
    "orders": 60,       # 1 min
}

# Rate limits (requests per second) per endpoint type
RATE_LIMITS = {
    "catalog": 2,
    "listings": 5,
    "pricing": 1,
    "inventory": 2,
    "orders": 2,
}


class SPAPIConnector:
    """Amazon SP-API client with automatic token refresh, rate limiting,
    Redis caching, and circuit breaker."""

    def __init__(
        self,
        tenant_id: str,
        refresh_token_encrypted: str,
        redis_client=None,
        http_client: httpx.AsyncClient | None = None,
        region: str = "na",
        sandbox: bool = False,
    ):
        self.tenant_id = tenant_id
        self._refresh_token_encrypted = refresh_token_encrypted
        self._redis = redis_client
        self._http = http_client
        self._owns_http = http_client is None
        self._base_url = SANDBOX_ENDPOINT if sandbox else REGION_ENDPOINTS.get(region, REGION_ENDPOINTS["na"])

        self._access_token: str | None = None
        self._token_expires_at: datetime = datetime.now(timezone.utc) - timedelta(hours=1)

        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self._rate_limiters: dict[str, asyncio.Semaphore] = {}
        self._last_call_times: dict[str, float] = {}

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient()
        return self._http

    async def close(self):
        if self._owns_http and self._http:
            await self._http.aclose()

    # ── Token Management ──────────────────────────────────────────

    async def _ensure_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        now = datetime.now(timezone.utc)
        buffer = timedelta(minutes=5)

        if self._access_token and self._token_expires_at > now + buffer:
            return self._access_token

        # Refresh token
        refresh_token = decrypt_token(self._refresh_token_encrypted)
        await self._refresh_access_token(refresh_token)
        return self._access_token

    async def _refresh_access_token(self, refresh_token: str) -> None:
        """Call Amazon LWA to get a new access token."""
        http = await self._get_http()
        response = await http.post(
            LWA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": SP_API_CLIENT_ID,
                "client_secret": SP_API_CLIENT_SECRET,
            },
        )
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        logger.info("sp_api_token_refreshed", tenant_id=self.tenant_id)

    # ── Rate Limiting ─────────────────────────────────────────────

    async def _rate_limit(self, endpoint_type: str) -> None:
        """Simple rate limiter with inter-call delay."""
        limit = RATE_LIMITS.get(endpoint_type, 2)
        delay = 1.0 / limit
        now = time.monotonic()
        last = self._last_call_times.get(endpoint_type, 0)
        wait = delay - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call_times[endpoint_type] = time.monotonic()

    # ── Caching ───────────────────────────────────────────────────

    def _cache_key(self, endpoint_type: str, params: str) -> str:
        h = hashlib.md5(params.encode()).hexdigest()[:12]
        return f"sp_api:{self.tenant_id}:{endpoint_type}:{h}"

    async def _get_cached(self, endpoint_type: str, params: str):
        if not self._redis:
            return None
        key = self._cache_key(endpoint_type, params)
        cached = await self._redis.get(key)
        if cached:
            logger.debug("sp_api_cache_hit", key=key)
            return json.loads(cached)
        return None

    async def _set_cached(self, endpoint_type: str, params: str, data) -> None:
        if not self._redis:
            return
        key = self._cache_key(endpoint_type, params)
        ttl = CACHE_TTLS.get(endpoint_type, 300)
        await self._redis.set(key, json.dumps(data), ex=ttl)

    # ── Core Request ──────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        endpoint_type: str,
        params: dict | None = None,
        body: dict | None = None,
        cache_params: str | None = None,
        max_retries: int = 3,
    ):
        """Make an authenticated SP-API request with retry, rate limiting, caching, and circuit breaker."""
        # Check cache
        if cache_params and method == "GET":
            cached = await self._get_cached(endpoint_type, cache_params)
            if cached is not None:
                return cached

        # Circuit breaker check
        self._circuit_breaker.check()

        # Rate limit
        await self._rate_limit(endpoint_type)

        # Ensure valid token
        token = await self._ensure_token()

        http = await self._get_http()
        url = f"{self._base_url}{path}"
        headers = {
            "x-amz-access-token": token,
            "Content-Type": "application/json",
        }

        for attempt in range(max_retries + 1):
            try:
                response = await http.request(
                    method, url, headers=headers, params=params, json=body
                )

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "2"))
                    if attempt < max_retries:
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()

                if response.status_code == 503 and attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue

                response.raise_for_status()

                data = response.json()
                self._circuit_breaker.record_success()

                # Cache the result
                if cache_params and method == "GET":
                    payload = data.get("payload", data)
                    await self._set_cached(endpoint_type, cache_params, payload)
                    return payload

                return data.get("payload", data)

            except CircuitBreakerOpen:
                raise
            except Exception as exc:
                self._circuit_breaker.record_failure()
                logger.error("sp_api_request_failed", path=path, attempt=attempt, error=str(exc))
                if attempt == max_retries:
                    raise

    # ── Public API Methods ────────────────────────────────────────

    async def get_listings(self, marketplace_id: str, next_token: str | None = None):
        """Get seller's listings for a marketplace."""
        params = {"marketplaceIds": marketplace_id}
        if next_token:
            params["nextToken"] = next_token
        result = await self._request(
            "GET", "/listings/2021-08-01/items",
            endpoint_type="listings",
            params=params,
            cache_params=f"listings:{marketplace_id}:{next_token}",
        )
        return result.get("items", []) if isinstance(result, dict) else result

    async def get_catalog_item(self, asin: str):
        """Get catalog item details."""
        return await self._request(
            "GET", f"/catalog/2022-04-01/items/{asin}",
            endpoint_type="catalog",
            cache_params=f"catalog:{asin}",
        )

    async def get_pricing(self, asin: str):
        """Get pricing info for an ASIN."""
        result = await self._request(
            "GET", "/products/pricing/v0/price",
            endpoint_type="pricing",
            params={"Asins": asin, "ItemType": "Asin"},
            cache_params=f"pricing:{asin}",
        )
        return result if isinstance(result, list) else [result]

    async def get_inventory(self, asin: str):
        """Get inventory summary for an ASIN."""
        result = await self._request(
            "GET", "/fba/inventory/v1/summaries",
            endpoint_type="inventory",
            params={"sellerSkus": asin, "granularityType": "Marketplace"},
            cache_params=f"inventory:{asin}",
        )
        return result.get("inventorySummaries", []) if isinstance(result, dict) else result

    async def update_listing(self, marketplace_id: str, sku: str, body: dict):
        """Update a listing."""
        return await self._request(
            "PUT", f"/listings/2021-08-01/items/{sku}",
            endpoint_type="listings",
            params={"marketplaceIds": marketplace_id},
            body=body,
        )

    async def get_orders(self, created_after: str, marketplace_id: str):
        """Get orders created after a given date."""
        result = await self._request(
            "GET", "/orders/v0/orders",
            endpoint_type="orders",
            params={"CreatedAfter": created_after, "MarketplaceIds": marketplace_id},
            cache_params=f"orders:{marketplace_id}:{created_after}",
        )
        return result.get("Orders", []) if isinstance(result, dict) else result
