import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()

app = FastAPI(title="Seller Autopilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _check_database() -> str:
    """Ping PostgreSQL with SELECT 1."""
    try:
        import asyncpg

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://seller_autopilot:localdev@localhost:5432/seller_autopilot",
        )
        # asyncpg expects postgres:// scheme
        dsn = db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.fetchval("SELECT 1")
            return "connected"
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        return "disconnected"


async def _check_redis() -> str:
    """Ping Redis."""
    try:
        import redis.asyncio as aioredis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = aioredis.from_url(redis_url)
        try:
            result = await r.ping()  # type: ignore[misc]
            if result:
                return "connected"
            return "disconnected"
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("redis_health_check_failed", error=str(exc))
        return "disconnected"


@app.get("/health")
async def health_check():
    db_status = await _check_database()
    redis_status = await _check_redis()

    status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"
    status_code = 200 if status == "healthy" else 503

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={
            "status": status,
            "database": db_status,
            "redis": redis_status,
            "version": "0.1.0",
        },
        status_code=status_code,
    )
