"""Auth request/response schemas using Pydantic v2."""

import re

from pydantic import BaseModel, EmailStr, field_validator


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    companyName: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class SignupResponse(BaseModel):
    tenantId: str
    userId: str
    email: str
    name: str
    accessToken: str
    refreshToken: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    tenantId: str
    userId: str
    email: str
    role: str
    accessToken: str
    refreshToken: str


class RefreshRequest(BaseModel):
    refreshToken: str


class RefreshResponse(BaseModel):
    accessToken: str


class MeResponse(BaseModel):
    userId: str
    email: str
    name: str
    role: str
    tenantId: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
