"""Authentication routes for registration, login, Google Sign-In, profile, and logout."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    LogoutResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_dependencies import get_current_user
from app.services.auth_service import (
    authenticate_google_user,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
    description="Registers a new user with email and password. Self-registration is strictly restricted to Student role.",
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, token, expires_in = await register_user(db, request)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
    description="Validates user credentials against stored Argon2 hashes and issues a signed JWT access token.",
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, token, expires_in = await authenticate_user(db, request)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate with Google Identity Services",
    description="Verifies a Google OAuth2 ID token, links existing verified accounts, or provisions a new Student account.",
)
async def google_auth(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, token, expires_in = await authenticate_google_user(db, request)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current user profile",
    description="Returns authenticated user details extracted from a validated JWT bearer token.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Terminate session",
    description="Terminates client session. Because JWT tokens are stateless, clients must discard the stored token.",
)
async def logout(
    current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    return LogoutResponse(message=f"Session closed for {current_user.email}. Discard token client-side.")

