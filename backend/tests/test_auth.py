"""Automated security and functional tests for CampusOps AI authentication backend."""

from datetime import datetime, timedelta, timezone
import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.mark.asyncio
async def test_password_hashing_and_verification():
    """Verify that password hashing uses Argon2 and verifies correctly."""
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)

    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password(plain, None) is False


@pytest.mark.asyncio
async def test_successful_registration(client: AsyncClient, db_session: AsyncSession):
    """Test user registration assigns student role and returns valid token."""
    payload = {
        "email": "student1@campus.edu",
        "name": "Alex Student",
        "password": "Password123!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "student1@campus.edu"
    assert data["user"]["name"] == "Alex Student"
    assert data["user"]["role"] == "student"
    assert data["user"]["is_active"] is True
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_student_role_forced_and_extra_fields_forbidden(client: AsyncClient):
    """Verify that self-registration strictly rejects any injected role field."""
    # Attempt privilege escalation by injecting role='admin'
    payload = {
        "email": "hacker@campus.edu",
        "name": "Sneaky User",
        "password": "Password123!",
        "role": "admin",
    }
    response = await client.post("/api/auth/register", json=payload)
    # Extra fields must be forbidden by Pydantic schema validation
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_registration_rejection(client: AsyncClient):
    """Test that registering an existing email returns 409 Conflict."""
    payload = {
        "email": "dup@campus.edu",
        "name": "Original User",
        "password": "Password123!",
    }
    r1 = await client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201

    # Attempt duplicate registration with different casing
    payload_dup = {
        "email": "DUP@campus.edu",
        "name": "Duplicate User",
        "password": "Password123!",
    }
    r2 = await client.post("/api/auth/register", json=payload_dup)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_successful_login(client: AsyncClient):
    """Test login with registered credentials returns token and profile."""
    reg_payload = {
        "email": "login_user@campus.edu",
        "name": "Login User",
        "password": "ValidPassword999!",
    }
    await client.post("/api/auth/register", json=reg_payload)

    login_payload = {
        "email": "login_user@campus.edu",
        "password": "ValidPassword999!",
    }
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_user@campus.edu"


@pytest.mark.asyncio
async def test_invalid_password_rejection(client: AsyncClient):
    """Test login rejection with invalid password returns 401 with generic message."""
    reg_payload = {
        "email": "testpass@campus.edu",
        "name": "Test User",
        "password": "CorrectPassword123!",
    }
    await client.post("/api/auth/register", json=reg_payload)

    bad_payload = {
        "email": "testpass@campus.edu",
        "password": "WrongPassword999!",
    }
    response = await client.post("/api/auth/login", json=bad_payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_get_me_profile_with_valid_token(client: AsyncClient):
    """Test /api/auth/me returns current user information."""
    reg_payload = {
        "email": "me_test@campus.edu",
        "name": "Me Tester",
        "password": "Password123!",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me_test@campus.edu"
    assert response.json()["role"] == "student"


@pytest.mark.asyncio
async def test_inactive_user_cannot_authenticate(client: AsyncClient, db_session: AsyncSession):
    """Test that deactivated users cannot log in and their existing tokens are rejected."""
    reg_payload = {
        "email": "deactivated@campus.edu",
        "name": "Deactivated User",
        "password": "Password123!",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    # Deactivate user directly in database
    stmt = select(User).where(User.email == "deactivated@campus.edu")
    user = (await db_session.execute(stmt)).scalar_one()
    user.is_active = False
    await db_session.commit()

    # 1. Attempt login with inactive account
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "deactivated@campus.edu", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "deactivated" in login_res.json()["detail"].lower()

    # 2. Attempt using prior token
    me_res = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 403


@pytest.mark.asyncio
async def test_jwt_expiry_and_invalid_signature(client: AsyncClient, db_session: AsyncSession):
    """Test that expired tokens and forged signatures are rejected."""
    reg_payload = {
        "email": "jwt_test@campus.edu",
        "name": "JWT Tester",
        "password": "Password123!",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    user_id = reg_res.json()["user"]["id"]

    # 1. Expired token
    expired_payload = {
        "sub": user_id,
        "email": "jwt_test@campus.edu",
        "role": "student",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=60),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    r_expired = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert r_expired.status_code == 401
    assert "expired" in r_expired.json()["detail"].lower()

    # 2. Forged signature
    forged_token = jwt.encode(
        {"sub": user_id, "email": "jwt_test@campus.edu", "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "wrong_fake_secret_key_12345678901234567890",
        algorithm=settings.jwt_algorithm,
    )
    r_forged = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert r_forged.status_code == 401
    assert "invalid" in r_forged.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_auth_missing_client_id_rejection(client: AsyncClient):
    """Verify that Google authentication rejects tokens with 503 when GOOGLE_CLIENT_ID is not configured."""
    original_client_id = settings.google_client_id
    try:
        settings.google_client_id = ""
        fake_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMyJ9.eyJuYW1lIjoiRmFrZSJ9.signature"
        response = await client.post("/api/auth/google", json={"id_token": fake_token})
        assert response.status_code == 503
        assert "not configured on this server" in response.json()["detail"].lower()
    finally:
        settings.google_client_id = original_client_id


@pytest.mark.asyncio
async def test_google_auth_audience_mismatch_rejection(client: AsyncClient, monkeypatch):
    """Verify that Google authentication strictly enforces audience matching and rejects mismatches."""
    original_client_id = settings.google_client_id
    try:
        settings.google_client_id = "configured-app-client-id.apps.googleusercontent.com"
        
        # Mock google_id_token.verify_oauth2_token to simulate an audience mismatch
        from google.oauth2 import id_token as google_id_token

        def mock_verify(*args, **kwargs):
            raise ValueError("Wrong recipient, payload audience doesn't match")

        monkeypatch.setattr(google_id_token, "verify_oauth2_token", mock_verify)

        response = await client.post("/api/auth/google", json={"id_token": "some.token.value"})
        assert response.status_code == 401
        assert "payload audience doesn't match" in response.json()["detail"].lower()
    finally:
        settings.google_client_id = original_client_id


def test_production_startup_rejects_development_jwt_secret():
    """Verify that Settings prevents production from starting with the development fallback secret."""
    from app.config import DEV_FALLBACK_JWT_SECRET, Settings

    # 1. Dev fallback secret in production (debug=False) must raise ValueError
    with pytest.raises(ValueError, match="Production security violation"):
        Settings(debug=False, jwt_secret_key=DEV_FALLBACK_JWT_SECRET)

    # 2. Too short secret in production must raise ValueError
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(debug=False, jwt_secret_key="short_secret")

    # 3. Valid production secret succeeds
    valid_prod = Settings(
        debug=False,
        jwt_secret_key="a_proper_unique_production_secret_key_2026_campusops",
    )
    assert valid_prod.debug is False
    assert valid_prod.jwt_secret_key == "a_proper_unique_production_secret_key_2026_campusops"


@pytest.mark.asyncio
async def test_google_invalid_token_rejection(client: AsyncClient):
    """Test that invalid Google OAuth tokens are rejected with 401 when client ID is configured."""
    original_client_id = settings.google_client_id
    try:
        settings.google_client_id = "test-client-id.apps.googleusercontent.com"
        fake_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMyJ9.eyJuYW1lIjoiRmFrZSJ9.signature"
        response = await client.post("/api/auth/google", json={"id_token": fake_token})
        assert response.status_code == 401
        assert "google authentication failed" in response.json()["detail"].lower()
    finally:
        settings.google_client_id = original_client_id


@pytest.mark.asyncio
async def test_role_authorization_enforcement(client: AsyncClient, db_session: AsyncSession):
    """Verify that student tokens are rejected from admin-required dependencies."""
    from fastapi import Depends
    from app.main import app
    from app.services.auth_dependencies import require_admin, require_support

    # Register temporary test routes on app to verify require_support and require_admin
    @app.get("/api/test-admin-gate")
    async def admin_gate(user: User = Depends(require_admin)):
        return {"status": "ok", "user": user.email}

    @app.get("/api/test-support-gate")
    async def support_gate(user: User = Depends(require_support)):
        return {"status": "ok", "user": user.email}

    # Register student
    reg_payload = {
        "email": "student_access@campus.edu",
        "name": "Access Tester",
        "password": "Password123!",
    }
    reg_res = await client.post("/api/auth/register", json=reg_payload)
    student_token = reg_res.json()["access_token"]

    # Student accessing admin gate -> 403 Forbidden
    res_admin = await client.get(
        "/api/test-admin-gate",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_admin.status_code == 403
    assert "administrator privileges" in res_admin.json()["detail"].lower()

    # Student accessing support gate -> 403 Forbidden
    res_support = await client.get(
        "/api/test-support-gate",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_support.status_code == 403
    assert "it support staff" in res_support.json()["detail"].lower()

    # Promote user to support directly
    stmt = select(User).where(User.email == "student_access@campus.edu")
    user = (await db_session.execute(stmt)).scalar_one()
    user.role = UserRole.SUPPORT
    await db_session.commit()

    # Fetch new token as support
    support_token, _ = create_access_token(user.id, user.email, user.role)

    # Support accessing support gate -> 200 OK
    res_support_ok = await client.get(
        "/api/test-support-gate",
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert res_support_ok.status_code == 200

    # Support accessing admin gate -> still 403 Forbidden!
    res_admin_deny = await client.get(
        "/api/test-admin-gate",
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert res_admin_deny.status_code == 403

    # Promote user to admin
    user.role = UserRole.ADMIN
    await db_session.commit()
    admin_token, _ = create_access_token(user.id, user.email, user.role)

    # Admin accessing admin gate -> 200 OK
    res_admin_ok = await client.get(
        "/api/test-admin-gate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_ok.status_code == 200
