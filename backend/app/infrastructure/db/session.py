"""Async engine va sessiya fabrikasi."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, settings


def build_engine(config: Settings | None = None) -> AsyncEngine:
    config = config or settings
    kwargs: dict[str, object] = {
        "echo": config.db_echo,
        "future": True,
        "pool_pre_ping": True,
    }
    # SQLite (testlar) uchun pool parametrlari qo'llanilmaydi.
    if not config.database_url.startswith("sqlite"):
        kwargs.update(
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_recycle=config.db_pool_recycle,
        )
    return create_async_engine(config.database_url, **kwargs)


engine: AsyncEngine = build_engine()

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Skriptlar va fon vazifalari uchun sessiya konteksti."""
    session = SessionFactory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    await engine.dispose()
