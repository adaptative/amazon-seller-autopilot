"""Auth business logic."""

import uuid
from datetime import datetime, timezone

import jwt
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger()


class AuthError(Exception):
    """Auth-specific error with code and message."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def signup(
    session: AsyncSession,
    name: str,
    email: str,
    password: str,
    company_name: str,
) -> dict:
    """Create a new tenant and user. Returns signup response dict."""
    email_lower = email.lower()

    # Check if email already exists
    result = await session.execute(
        text("SELECT id FROM users WHERE LOWER(email) = :email"),
        {"email": email_lower},
    )
    if result.fetchone():
        raise AuthError("EMAIL_ALREADY_EXISTS", "An account with this email already exists", 409)

    # Create tenant
    tenant_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO tenants (id, name, slug, subscription_tier, status) "
            "VALUES (:id, :name, :slug, 'starter', 'active')"
        ),
        {
            "id": str(tenant_id),
            "name": company_name,
            "slug": f"tenant-{tenant_id.hex[:8]}",
        },
    )

    # Create user
    user_id = uuid.uuid4()
    password_hashed = hash_password(password)
    await session.execute(
        text(
            "INSERT INTO users (id, tenant_id, email, name, role, password_hash) "
            "VALUES (:id, :tid, :email, :name, 'owner', :pw)"
        ),
        {
            "id": str(user_id),
            "tid": str(tenant_id),
            "email": email_lower,
            "name": name,
            "pw": password_hashed,
        },
    )

    await session.commit()

    access_token = create_access_token(tenant_id, user_id)
    refresh_token = create_refresh_token(tenant_id, user_id)

    return {
        "tenantId": str(tenant_id),
        "userId": str(user_id),
        "email": email_lower,
        "name": name,
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


async def login(
    session: AsyncSession,
    email: str,
    password: str,
) -> dict:
    """Authenticate user and return tokens."""
    email_lower = email.lower()

    # Set RLS context to empty — we need to search across tenants for login
    # Use admin-level query (the service should run with appropriate permissions)
    result = await session.execute(
        text(
            "SELECT id, tenant_id, email, name, role, password_hash "
            "FROM users WHERE LOWER(email) = :email"
        ),
        {"email": email_lower},
    )
    user = result.fetchone()

    if not user:
        raise AuthError(
            "INVALID_CREDENTIALS",
            "Invalid email or password",
            401,
        )

    if not verify_password(password, user.password_hash):
        raise AuthError(
            "INVALID_CREDENTIALS",
            "Invalid email or password",
            401,
        )

    # Update last_login_at
    await session.execute(
        text("UPDATE users SET last_login_at = :now WHERE id = :uid"),
        {"now": datetime.now(timezone.utc), "uid": str(user.id)},
    )
    await session.commit()

    access_token = create_access_token(user.tenant_id, user.id)
    refresh_token = create_refresh_token(user.tenant_id, user.id)

    return {
        "tenantId": str(user.tenant_id),
        "userId": str(user.id),
        "email": user.email,
        "role": user.role,
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


def refresh_access_token(refresh_token_str: str) -> dict:
    """Validate refresh token and generate new access token."""
    try:
        payload = decode_token(refresh_token_str)
    except jwt.ExpiredSignatureError:
        raise AuthError("TOKEN_EXPIRED", "Refresh token has expired", 401)
    except jwt.PyJWTError:
        raise AuthError("INVALID_TOKEN", "Invalid refresh token", 401)

    if payload.get("type") != "refresh":
        raise AuthError("INVALID_TOKEN", "Not a refresh token", 401)

    tenant_id = uuid.UUID(payload["tenant_id"])
    user_id = uuid.UUID(payload["user_id"])
    new_access = create_access_token(tenant_id, user_id)

    return {"accessToken": new_access}


async def get_current_user(
    session: AsyncSession,
    token: str,
) -> dict:
    """Extract user from JWT claims and fetch from DB."""
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthError("TOKEN_EXPIRED", "Access token has expired", 401)
    except jwt.PyJWTError:
        raise AuthError("INVALID_TOKEN", "Invalid access token", 401)

    if payload.get("type") != "access":
        raise AuthError("INVALID_TOKEN", "Not an access token", 401)

    user_id = payload.get("user_id")
    tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        raise AuthError("INVALID_TOKEN", "Token missing required claims", 401)

    # Set RLS context for this request
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": tenant_id},
    )

    result = await session.execute(
        text("SELECT id, email, name, role, tenant_id FROM users WHERE id = :uid"),
        {"uid": user_id},
    )
    user = result.fetchone()

    if not user:
        raise AuthError("USER_NOT_FOUND", "User not found", 401)

    return {
        "userId": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tenantId": str(user.tenant_id),
    }
