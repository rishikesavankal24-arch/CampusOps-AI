"""Secure offline CLI utility for provisioning the initial Administrator account.

SAFEGUARDS:
- Never accepts hardcoded passwords.
- Enforces minimum 8-character password complexity.
- Requires explicit interactive confirmation or validated environment variables.
- Promotes existing accounts safely without duplicating records.
"""

import argparse
import asyncio
import getpass
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


async def provision_admin(email: str, name: str, password: str, session: AsyncSession | None = None) -> None:
    """Safely provision or promote an administrator account."""
    # Validate email
    try:
        valid = validate_email(email, check_deliverability=False)
        normalized_email = valid.normalized.lower()
    except EmailNotValidError as e:
        raise ValueError(f"Invalid email format: {e}")

    # Validate password complexity
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not name or len(name.strip()) < 2:
        raise ValueError("Name must be at least 2 characters long")

    async def _execute(s: AsyncSession) -> None:
        stmt = select(User).where(User.email == normalized_email)
        result = await s.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            print(f"User '{normalized_email}' already exists. Current role: {user.role.value}")
            user.role = UserRole.ADMIN
            user.name = name.strip()
            user.password_hash = hash_password(password)
            user.is_active = True
            await s.commit()
            print(f"Success: Existing account '{normalized_email}' promoted to {UserRole.ADMIN.value}.")
        else:
            new_admin = User(
                email=normalized_email,
                name=name.strip(),
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            s.add(new_admin)
            await s.commit()
            print(f"Success: Administrator account '{normalized_email}' provisioned successfully.")

    if session:
        await _execute(session)
    else:
        async with AsyncSessionLocal() as s:
            await _execute(s)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Secure offline CLI tool to provision or promote a CampusOps AI administrator."
    )
    parser.add_argument("--email", help="Administrator email (or set ADMIN_EMAIL env var)")
    parser.add_argument("--name", help="Administrator full name (or set ADMIN_NAME env var)")
    parser.add_argument("--password", help="Administrator password (or set ADMIN_PASSWORD env var; prompts interactively if omitted)")

    args = parser.parse_args()

    email = args.email or os.getenv("ADMIN_EMAIL")
    name = args.name or os.getenv("ADMIN_NAME")
    password = args.password or os.getenv("ADMIN_PASSWORD")

    if not email:
        email = input("Enter Administrator Email: ").strip()

    if not name:
        name = input("Enter Administrator Full Name: ").strip()

    if not password:
        password = getpass.getpass("Enter Administrator Password (min 8 chars): ")
        password_confirm = getpass.getpass("Confirm Administrator Password: ")
        if password != password_confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    try:
        asyncio.run(provision_admin(email=email, name=name, password=password))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
