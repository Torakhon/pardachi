"""Testlar uchun umumiy fixture'lar."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="pardachi-test-"))

# Muhit o'zgaruvchilari ilova importidan OLDIN o'rnatiladi.
os.environ.update(
    DATABASE_URL=f"sqlite+aiosqlite:///{TEST_DIR / 'test.db'}",
    SECRET_KEY="test-secret-key-for-unit-tests-only-0123456789",
    TELEGRAM_BOT_TOKEN="123456:TEST-BOT-TOKEN",
    ALLOW_DEV_LOGIN="true",
    DEV_LOGIN_SECRET="test-secret",
    MEDIA_ROOT=str(TEST_DIR / "media"),
    STORAGE_BACKEND="local",
    RATE_LIMIT_PER_MINUTE="0",
    ENVIRONMENT="development",
    LOG_LEVEL="WARNING",
    FIRST_USER_IS_ADMIN="false",
)

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.api.deps import get_db_session  # noqa: E402
from app.domain.models import Base, Team, User  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_session():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    app.dependency_overrides.clear()


async def login(client: AsyncClient, *, role: str = "measurer", telegram_id: int = 555000111) -> dict:
    """Dev-login orqali token oladi va sarlavhalarni qaytaradi."""
    response = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "secret": "test-secret",
            "telegram_id": telegram_id,
            "first_name": "Test",
            "role": role,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def auth_headers(
    client: AsyncClient, *, role: str = "measurer", telegram_id: int = 555000111
) -> dict[str, str]:
    data = await login(client, role=role, telegram_id=telegram_id)
    return {"Authorization": f"Bearer {data['access_token']}"}


async def create_team(session_factory, name: str) -> Team:
    """Bazada to'g'ridan-to'g'ri jamoa yaratadi."""
    async with session_factory() as session:
        team = Team(name=name)
        session.add(team)
        await session.commit()
        return team


async def assign_team(session_factory, telegram_id: int, team: Team | None) -> None:
    """Dev-login orqali yaratilgan foydalanuvchini jamoaga biriktiradi."""
    from sqlalchemy import select

    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one()
        user.team_id = team.id if team is not None else None
        await session.commit()


async def member_headers(
    client: AsyncClient,
    session_factory,
    *,
    role: str,
    telegram_id: int,
    team: Team | None,
) -> dict[str, str]:
    """Berilgan rol va jamoadagi foydalanuvchi uchun sarlavhalar."""
    headers = await auth_headers(client, role=role, telegram_id=telegram_id)
    await assign_team(session_factory, telegram_id, team)
    return headers


@pytest.fixture
async def team(session_factory) -> Team:
    return await create_team(session_factory, "Toshkent jamoasi")


@pytest.fixture
async def other_team(session_factory) -> Team:
    return await create_team(session_factory, "Samarqand jamoasi")


@pytest.fixture
async def measurer_headers(client: AsyncClient, session_factory, team: Team) -> dict[str, str]:
    """Birinchi jamoaning o'lchovchisi."""
    return await member_headers(client, session_factory, role="measurer", telegram_id=555000111, team=team)


@pytest.fixture
async def teammate_headers(client: AsyncClient, session_factory, team: Team) -> dict[str, str]:
    """Xuddi shu jamoadagi ikkinchi o'lchovchi."""
    return await member_headers(client, session_factory, role="measurer", telegram_id=555000333, team=team)


@pytest.fixture
async def viewer_headers(client: AsyncClient, session_factory, team: Team) -> dict[str, str]:
    """Birinchi jamoaning ko'ruvchisi (faqat o'qish huquqi)."""
    return await member_headers(client, session_factory, role="viewer", telegram_id=555000444, team=team)


@pytest.fixture
async def other_headers(client: AsyncClient, session_factory, other_team: Team) -> dict[str, str]:
    """Boshqa jamoaning o'lchovchisi."""
    return await member_headers(
        client, session_factory, role="measurer", telegram_id=555000555, team=other_team
    )


@pytest.fixture
async def teamless_headers(client: AsyncClient, session_factory) -> dict[str, str]:
    """Hech qanday jamoaga biriktirilmagan o'lchovchi."""
    return await member_headers(client, session_factory, role="measurer", telegram_id=555000666, team=None)


@pytest.fixture
async def admin_headers(client: AsyncClient, session_factory, team: Team) -> dict[str, str]:
    return await auth_headers(client, role="admin", telegram_id=555000222)


@pytest.fixture
def project_payload() -> dict:
    return {
        "name": "Test obyekt",
        "order_number": "OB-TEST-001",
        "customer_name": "Sardor Aliyev",
        "customer_phone": "901234567",
        "address": "Toshkent sh., Chilonzor 12",
        "note": "Sinov uchun",
    }
