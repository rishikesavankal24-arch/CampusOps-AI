"""Automated tests for admin provisioning safeguards in seed_admin script."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from scripts.seed_admin import provision_admin


@pytest.mark.asyncio
async def test_admin_seed_rejects_invalid_email(db_session: AsyncSession):
    """Verify that seed_admin rejects malformed email addresses."""
    with pytest.raises(ValueError, match="Invalid email format"):
        await provision_admin(email="notanemail", name="Admin", password="Password123!", session=db_session)


@pytest.mark.asyncio
async def test_admin_seed_rejects_short_password(db_session: AsyncSession):
    """Verify that seed_admin rejects passwords shorter than 8 characters."""
    with pytest.raises(ValueError, match="at least 8 characters"):
        await provision_admin(email="admin@campus.edu", name="Admin", password="short", session=db_session)


@pytest.mark.asyncio
async def test_admin_seed_provisions_and_promotes(db_session: AsyncSession):
    """Verify that seed_admin creates an admin account and safely promotes existing accounts."""
    admin_email = "superadmin@campusops.edu"

    # 1. Provision fresh admin
    await provision_admin(email=admin_email, name="Super Admin", password="ComplexAdminPassword2026!", session=db_session)

    stmt = select(User).where(User.email == admin_email)
    user = (await db_session.execute(stmt)).scalar_one()

    assert user.role == UserRole.ADMIN
    assert user.name == "Super Admin"
    assert user.is_active is True
    assert user.password_hash.startswith("$argon2id$")

    # 2. Promote an existing student account
    student_email = "promoted_student@campusops.edu"
    student = User(
        email=student_email,
        name="Student Alex",
        password_hash="somehash",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    await db_session.commit()

    await provision_admin(email=student_email, name="Alex Admin", password="NewAdminPassword2026!", session=db_session)

    await db_session.refresh(student)
    assert student.role == UserRole.ADMIN
    assert student.name == "Alex Admin"
