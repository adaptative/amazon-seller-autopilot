"""FastAPI middleware stack: TenantContext, RateLimit, RequestLogging, ErrorHandler."""

import os
import time
import traceback
import uuid

import jwt
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import JWT_ALGORITHM, JWT_SECRET

logger = structlog.get_logger()

# Paths that skip authentication
PUBLIC_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})
PUBLIC_PREFIXES = ("/api/v1/auth/",)

# Rate limit tiers (requests per minute)
RATE_LIMITS = {
    "starter": 100,
    "growth": 500,
    "professional": 2000,
    "enterprise": 10000,
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _is_public_path(path: str) -> bool:
    """Check if path should skip authentication."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _error_json(code: str, message: str, request_id: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "requestId": request_id}},
    )


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract JWT, decode, inject tenant_id + user_id into request.state."""

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        if _is_public_path(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error_json("UNAUTHORIZED", "Missing or invalid authorization header", request_id, 401)

        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return _error_json("TOKEN_EXPIRED", "Access token has expired", request_id, 401)
        except jwt.PyJWTError:
            return _error_json("UNAUTHORIZED", "Invalid access token", request_id, 401)

        tenant_id = payload.get("tenant_id")
        user_id = payload.get("user_id")

        if not tenant_id or not user_id:
            return _error_json("UNAUTHORIZED", "Token missing required claims", request_id, 401)

        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        request.state.subscription_tier = payload.get("subscription_tier", "starter")

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant rate limiting using Redis."""

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self._redis = redis_client

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(REDIS_URL)
            return self._redis
        except Exception:
            return None

    async def dispatch(self, request: Request, call_next):
        if _is_public_path(request.url.path):
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)

        tier = getattr(request.state, "subscription_tier", "starter")
        limit = RATE_LIMITS.get(tier, 100)

        redis = await self._get_redis()
        if redis:
            try:
                minute = int(time.time()) // 60
                key = f"ratelimit:{tenant_id}:{minute}"
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, 120)

                if count > limit:
                    request_id = getattr(request.state, "request_id", "")
                    return JSONResponse(
                        status_code=429,
                        content={"error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded. Limit: {limit}/min",
                            "requestId": request_id,
                        }},
                        headers={"Retry-After": "60"},
                    )
            except Exception as exc:
                logger.warning("rate_limit_check_failed", error=str(exc))

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Add X-Request-ID to every response and log requests with structlog."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.monotonic()
        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=latency_ms,
            tenant_id=getattr(request.state, "tenant_id", None),
            request_id=request_id,
        )

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch all exceptions. Log server-side, return safe JSON to client."""

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                error=str(exc),
                traceback=traceback.format_exc(),
                path=request.url.path,
                request_id=request_id,
            )
            return JSONResponse(
                status_code=500,
                content={"error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "requestId": request_id,
                }},
                headers={"X-Request-ID": request_id},
            )
