"""Authentication service handling password hashing, JWT operations, and Google token validation."""

from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Any
import jwt
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole
from app.schemas.auth import GoogleAuthRequest, UserLoginRequest, UserRegisterRequest

# Initialize Argon2 recommended password hasher
_password_hasher = PasswordHash.recommended()

VALID_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def hash_password(password: str) -> str:
    """Generate a secure Argon2 hash for the provided password."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plain password against the stored Argon2 hash safely."""
    if not hashed_password:
        return False
    try:
        return _password_hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(user_id: UUID, email: str, role: UserRole) -> tuple[str, int]:
    """Create a signed JWT access token with user claims and expiration."""
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire_time = datetime.now(timezone.utc) + expires_delta
    issued_at = datetime.now(timezone.utc)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role.value if hasattr(role, "value") else str(role),
        "exp": expire_time,
        "iat": issued_at,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_google_token(id_token_str: str) -> dict[str, Any]:
    """Verify Google Identity Services OAuth2 ID token signature, issuer, audience and claims.

    SECURITY:
    - Audience validation against GOOGLE_CLIENT_ID is strictly mandatory.
    - If GOOGLE_CLIENT_ID is not configured, Google authentication is immediately rejected
      with HTTP 503 rather than skipping audience validation.
    """
    client_id = settings.google_client_id.strip() if settings.google_client_id else ""
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured on this server",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        request = google_requests.Request()

        # Strict audience verification - never None
        claims = google_id_token.verify_oauth2_token(
            id_token_str,
            request,
            audience=client_id,
        )

        issuer = claims.get("iss")
        if issuer not in VALID_GOOGLE_ISSUERS:
            raise ValueError(f"Invalid token issuer: {issuer}")

        if not claims.get("email"):
            raise ValueError("Google token is missing an email claim")

        return claims
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed: Token verification error",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def register_user(
    db: AsyncSession,
    request: UserRegisterRequest,
) -> tuple[User, str, int]:
    """Register a new student account using email and password.
    
    SECURITY: Role is strictly forced to UserRole.STUDENT.
    """
    normalized_email = request.email.strip().lower()

    # Duplicate check
    existing_stmt = select(User).where(User.email == normalized_email)
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Force STUDENT role on self-registration
    new_user = User(
        email=normalized_email,
        name=request.name.strip(),
        password_hash=hash_password(request.password),
        role=UserRole.STUDENT,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token, expires_in = create_access_token(
        user_id=new_user.id,
        email=new_user.email,
        role=new_user.role,
    )
    return new_user, token, expires_in


async def authenticate_user(
    db: AsyncSession,
    request: UserLoginRequest,
) -> tuple[User, str, int]:
    """Authenticate user with email and password."""
    normalized_email = request.email.strip().lower()

    stmt = select(User).where(User.email == normalized_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Generic error message to prevent user enumeration
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator.",
        )

    token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    return user, token, expires_in


async def authenticate_google_user(
    db: AsyncSession,
    request: GoogleAuthRequest,
) -> tuple[User, str, int]:
    """Authenticate user with Google Identity Services ID token."""
    claims = verify_google_token(request.id_token)
    google_id = claims.get("sub")
    verified_email = claims.get("email", "").strip().lower()
    name = claims.get("name") or verified_email.split("@")[0]
    avatar_url = claims.get("picture")
    email_verified = claims.get("email_verified", False)

    # 1. Lookup by Google ID
    stmt_google = select(User).where(User.google_id == google_id)
    result_google = await db.execute(stmt_google)
    user = result_google.scalar_one_or_none()

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact an administrator.",
            )
        # Update avatar or name if updated on Google
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            await db.commit()
            await db.refresh(user)

        token, expires_in = create_access_token(user.id, user.email, user.role)
        return user, token, expires_in

    # 2. Lookup by Email
    stmt_email = select(User).where(User.email == verified_email)
    result_email = await db.execute(stmt_email)
    user_by_email = result_email.scalar_one_or_none()

    if user_by_email:
        if not user_by_email.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact an administrator.",
            )

        # Collision with a different Google account
        if user_by_email.google_id and user_by_email.google_id != google_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is linked to a different Google account",
            )

        # Link account only if Google verified email authenticity
        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account email is not verified by Google",
            )

        user_by_email.google_id = google_id
        if avatar_url and not user_by_email.avatar_url:
            user_by_email.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user_by_email)

        token, expires_in = create_access_token(user_by_email.id, user_by_email.email, user_by_email.role)
        return user_by_email, token, expires_in

    # 3. Provision new user (Always defaults to STUDENT)
    new_user = User(
        email=verified_email,
        name=name,
        google_id=google_id,
        avatar_url=avatar_url,
        password_hash=None,
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token, expires_in = create_access_token(new_user.id, new_user.email, new_user.role)
    return new_user, token, expires_in

