"""Pydantic schemas package for CampusOps AI."""

from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleAuthRequest,
    UserResponse,
    TokenResponse,
    LogoutResponse,
)

__all__ = [
    "UserRegisterRequest",
    "UserLoginRequest",
    "GoogleAuthRequest",
    "UserResponse",
    "TokenResponse",
    "LogoutResponse",
]

