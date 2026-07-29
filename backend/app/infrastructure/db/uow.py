"""Unit of Work — bitta so'rov doirasidagi tranzaksiya va repozitoriylar."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories import UnitOfWork
from app.infrastructure.repositories.audit_repository import SqlAlchemyAuditLogRepository
from app.infrastructure.repositories.project_repository import SqlAlchemyProjectRepository
from app.infrastructure.repositories.room_repository import (
    SqlAlchemyMeasurementItemRepository,
    SqlAlchemyProjectLocationRepository,
    SqlAlchemyRoomImageRepository,
    SqlAlchemyRoomRepository,
)
from app.infrastructure.repositories.user_repository import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = SqlAlchemyUserRepository(session)
        self.projects = SqlAlchemyProjectRepository(session)
        self.rooms = SqlAlchemyRoomRepository(session)
        self.items = SqlAlchemyMeasurementItemRepository(session)
        self.images = SqlAlchemyRoomImageRepository(session)
        self.locations = SqlAlchemyProjectLocationRepository(session)
        self.audit = SqlAlchemyAuditLogRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, instance: Any) -> None:
        await self.session.refresh(instance)

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, *_: object) -> None:
        if exc_type is not None:
            await self.rollback()
