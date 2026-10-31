"""Application configuration loaded from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings

DEV_FALLBACK_JWT_SECRET = "campusops_dev_jwt_secret_key_must_be_overridden_in_production_2026"


class Settings(BaseSettings):
    """Central configuration for the CampusOps AI backend.

    All values are loaded from environment variables or a .env file.
    Defaults are safe for local development; override in production.
    """

    # --- Application ---
    app_name: str = "CampusOps AI"
    app_version: str = "0.1.0"
    debug: bool = True

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- Database Settings ---
    postgres_host: str = "localhost"
    postgres_port: int = 5434
    postgres_db: str = "campusops_db"
    postgres_user: str = "campusops_admin"
    postgres_password: str = "campusops_secret_2026"

    # Async Database URL (defaulting to port 5434)
    database_url: str = (
        "postgresql+asyncpg://campusops_admin:campusops_secret_2026@localhost:5434/campusops_db"
    )

    # Sync Database URL for Alembic migrations
    sync_database_url: str = (
        "postgresql+psycopg://campusops_admin:campusops_secret_2026@localhost:5434/campusops_db"
    )

    # --- Google Gemini & RAG ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_model_fallback: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimension: int = 768
    rag_top_k: int = 4
    rag_similarity_threshold: float = 0.35
    rag_chunk_size: int = 600
    rag_chunk_overlap: int = 100

    @property
    def is_gemini_configured(self) -> bool:
        """Safely verify whether a Gemini API key is configured without exposing its value."""
        return bool(self.gemini_api_key and len(self.gemini_api_key.strip()) >= 16)

    # --- Authentication ---
    google_client_id: str = ""

    @property
    def is_google_configured(self) -> bool:
        """Safely verify whether Google OAuth Client ID is configured without exposing its value."""
        return bool(self.google_client_id and len(self.google_client_id.strip()) >= 10)

    jwt_secret_key: str = DEV_FALLBACK_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Ensure production environment cannot start with default development secrets."""
        if not self.debug:
            if self.jwt_secret_key == DEV_FALLBACK_JWT_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "Production security violation: When DEBUG=False, JWT_SECRET_KEY must be set "
                    "to a unique, cryptographically strong secret of at least 32 characters."
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
