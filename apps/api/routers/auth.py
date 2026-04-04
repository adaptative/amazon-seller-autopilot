"""Authentication API router."""

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
)
from services.auth_service import AuthError, get_current_user, login, refresh_access_token, signup

router = APIRouter(prefix="/api/v1", tags=["auth"])


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post("/auth/signup", response_model=SignupResponse, status_code=201)
async def signup_endpoint(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await signup(
            session=db,
            name=body.name,
            email=body.email,
            password=body.password,
            company_name=body.companyName,
        )
        return JSONResponse(status_code=201, content=result)
    except AuthError as e:
        return _error_response(e.code, e.message, e.status_code)


@router.post("/auth/login", response_model=LoginResponse)
async def login_endpoint(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await login(session=db, email=body.email, password=body.password)
        return result
    except AuthError as e:
        return _error_response(e.code, e.message, e.status_code)


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh_endpoint(body: RefreshRequest):
    try:
        result = refresh_access_token(body.refreshToken)
        return result
    except AuthError as e:
        return _error_response(e.code, e.message, e.status_code)


@router.get("/me", response_model=MeResponse)
async def me_endpoint(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        return _error_response("UNAUTHORIZED", "Missing or invalid authorization header", 401)

    token = authorization.split(" ", 1)[1]
    try:
        user_data = await get_current_user(session=db, token=token)
        return user_data
    except AuthError as e:
        return _error_response(e.code, e.message, e.status_code)
