"""Application configuration."""

import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://seller_autopilot:localdev@localhost:5432/seller_autopilot",
)

APP_DATABASE_URL = os.getenv(
    "APP_DATABASE_URL",
    "postgresql+asyncpg://app_user:app_user_pass@localhost:5432/seller_autopilot",
)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
