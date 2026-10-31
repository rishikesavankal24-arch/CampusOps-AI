"""Authentication Pydantic schemas for request validation and response serialization."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Schema for student self-registration.
    
    CRITICAL: 'role' is intentionally omitted and forbidden to prevent self-privilege escalation.
    """
    email: EmailStr = Field(..., description="Valid institutional or personal email address")
    name: str = Field(..., min_length=2, max_length=100, description="Full name of user")
    password: str = Field(..., min_length=8, max_length=128, description="Password (minimum 8 characters)")

    model_config = ConfigDict(extra="forbid")


class UserLoginRequest(BaseModel):
    """Schema for email/password authentication."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")

    model_config = ConfigDict(extra="forbid")


class GoogleAuthRequest(BaseModel):
    """Schema for Google Identity Services OAuth ID token verification."""
    id_token: str = Field(..., min_length=10, description="Signed Google OAuth2 JWT ID token")

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    """Safe user profile response.
    
    CRITICAL: password_hash and internal credentials are strictly excluded.
    """
    id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool
    avatar_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Authentication token response with JWT and user profile."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifespan in seconds")
    user: UserResponse


class LogoutResponse(BaseModel):
    """Response returned upon session termination."""
    message: str = "Logged out successfully"

