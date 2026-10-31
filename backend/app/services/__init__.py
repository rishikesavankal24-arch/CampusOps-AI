"""Services package export for CampusOps AI."""

from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    verify_google_token,
    register_user,
    authenticate_user,
    authenticate_google_user,
)
from app.services.auth_dependencies import (
    get_current_user,
    require_authenticated_user,
    require_support,
    require_admin,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "verify_google_token",
    "register_user",
    "authenticate_user",
    "authenticate_google_user",
    "get_current_user",
    "require_authenticated_user",
    "require_support",
    "require_admin",
]
