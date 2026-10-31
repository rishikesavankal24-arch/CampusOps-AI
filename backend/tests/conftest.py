"""Pytest configuration and fixtures for CampusOps AI test suite.

Uses an isolated test database (campusops_test_db) on the dedicated PostgreSQL container.
Never touches development or production database records.
"""

from collections.abc import AsyncGenerator
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401

TEST_DATABASE_URL = "postgresql+asyncpg://campusops_admin:campusops_secret_2026@localhost:5434/campusops_test_db"


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Truncate tables before each test to ensure complete isolation."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE users, incidents, evidence, chat_messages, knowledge_base, audit_logs, network_devices RESTART IDENTITY CASCADE;"
            )
        )
    await engine.dispose()
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    session = session_maker()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP test client with overridden database dependency."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        session = session_maker()
        try:
            yield session
        finally:
            await session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()
