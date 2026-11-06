import asyncio
from decimal import Decimal
import os
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.database import Base
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.account import Account
from app.models.user import User

# Use PostgreSQL if TEST_DATABASE_URL is provided, otherwise in-memory SQLite for unit tests
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DB_URL else {},
    poolclass=StaticPool if "sqlite" in TEST_DB_URL else None,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session")
async def prepare_database():
    """Create all tables before test session and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(prepare_database) -> AsyncGenerator[AsyncSession, None]:
    """Yield an isolated database session per test with rollback."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX async client with overridden db dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_user(db_session: AsyncSession) -> User:
    """Create a standard account holder user."""
    user = User(
        email="client.alice@example.com",
        password_hash=get_password_hash("SecretPassword123!"),
        full_name="Alice Smith",
        role="ACCOUNT_HOLDER",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client_bob(db_session: AsyncSession) -> User:
    """Create a second account holder user."""
    user = User(
        email="client.bob@example.com",
        password_hash=get_password_hash("SecretPassword123!"),
        full_name="Bob Jones",
        role="ACCOUNT_HOLDER",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an administrator user."""
    user = User(
        email="admin.root@example.com",
        password_hash=get_password_hash("AdminMasterPass123!"),
        full_name="Admin Chief",
        role="ADMIN",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auditor_user(db_session: AsyncSession) -> User:
    """Create an auditor user."""
    user = User(
        email="auditor.check@example.com",
        password_hash=get_password_hash("AuditorPass123!"),
        full_name="Eva Auditor",
        role="AUDITOR",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def get_auth_headers(user: User) -> dict:
    """Generate Authorization header with valid JWT."""
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"Authorization": f"Bearer {token}"}
