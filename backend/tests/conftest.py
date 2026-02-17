"""Shared fixtures for all tests. Uses SQLite for unit tests (no Postgres required)."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.opinion import Opinion, Question


# Use aiosqlite for tests — no Postgres/pgvector dependency needed
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def seeded_db(db_session):
    """DB session with an active question already created."""
    question = Question(
        text="When is it okay to lie?",
        slug="when-is-it-okay-to-lie",
        active=True,
    )
    db_session.add(question)
    await db_session.commit()
    await db_session.refresh(question)
    return db_session, question


@pytest.fixture
def mock_gemini():
    """Mock all Gemini AI calls."""
    fake_embedding = [0.1] * 768

    with (
        patch("app.services.opinions.get_embedding", new_callable=AsyncMock) as mock_embed,
        patch("app.services.opinions.strip_pii", new_callable=AsyncMock) as mock_pii,
        patch("app.services.opinions.detect_language", new_callable=AsyncMock) as mock_lang,
        patch("app.services.opinions.translate_to_english", new_callable=AsyncMock) as mock_translate,
    ):
        mock_embed.return_value = fake_embedding
        mock_pii.return_value = "An anonymized opinion about the topic."
        mock_lang.return_value = "en"
        mock_translate.return_value = "An anonymized opinion about the topic."

        yield {
            "get_embedding": mock_embed,
            "strip_pii": mock_pii,
            "detect_language": mock_lang,
            "translate_to_english": mock_translate,
            "embedding": fake_embedding,
        }


@pytest.fixture
def client(db_session):
    """HTTPX async client wired to test DB. Resets rate limiter each test."""
    from httpx import ASGITransport, AsyncClient

    from app.middleware.rate_limit import RateLimitMiddleware

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Reset rate limiter state between tests
    for middleware in app.user_middleware:
        if middleware.cls is RateLimitMiddleware:
            break
    # Walk the middleware stack to find and reset the rate limiter
    mw = app.middleware_stack
    while mw is not None:
        if isinstance(mw, RateLimitMiddleware):
            mw.reset()
            break
        mw = getattr(mw, "app", None)

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
