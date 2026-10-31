"""Routes package export for CampusOps AI."""

from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.incidents import router as incidents_router
from app.routes.knowledge import router as knowledge_router

__all__ = [
    "health_router",
    "auth_router",
    "chat_router",
    "knowledge_router",
    "incidents_router",
]
