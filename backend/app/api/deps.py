"""FastAPI bog'liqliklari (Dependency Injection)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.permissions import ensure_admin
from app.application.services.auth_service import AuthService
from app.application.services.image_service import ImageService
from app.application.services.measurement_service import MeasurementService
from app.application.services.project_service import ProjectService
from app.application.services.room_service import RoomService
from app.application.services.stats_service import StatsService
from app.application.services.team_service import TeamService
from app.application.services.user_service import UserService
from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, InactiveUserError
from app.core.logging import user_id_ctx
from app.core.security import decode_token
from app.domain.models import User
from app.domain.repositories import UnitOfWork
from app.infrastructure.db.session import SessionFactory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from app.infrastructure.storage.base import FileStorage
from app.infrastructure.storage.factory import get_storage

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session = SessionFactory()
    try:
        yield session
    finally:
        await session.close()


async def get_uow(session: Annotated[AsyncSession, Depends(get_db_session)]) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_config() -> Settings:
    return get_settings()


def get_file_storage() -> FileStorage:
    return get_storage()


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
UowDep = Annotated[UnitOfWork, Depends(get_uow)]
ConfigDep = Annotated[Settings, Depends(get_config)]
StorageDep = Annotated[FileStorage, Depends(get_file_storage)]


async def get_current_user(
    uow: UowDep,
    config: ConfigDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Avtorizatsiya tokeni yuborilmadi.")

    payload = decode_token(credentials.credentials, "access", config)
    user = await uow.users.get(payload.subject)
    if user is None:
        raise AuthenticationError("Foydalanuvchi topilmadi.")
    if not user.is_active:
        raise InactiveUserError()

    user_id_ctx.set(str(user.id))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    ensure_admin(user)
    return user


AdminUser = Annotated[User, Depends(get_current_admin)]


# --------------------------------------------------------------- servislar


def get_auth_service(uow: UowDep, config: ConfigDep) -> AuthService:
    return AuthService(uow, config)


def get_project_service(uow: UowDep) -> ProjectService:
    return ProjectService(uow)


def get_room_service(uow: UowDep) -> RoomService:
    return RoomService(uow)


def get_measurement_service(uow: UowDep) -> MeasurementService:
    return MeasurementService(uow)


def get_image_service(uow: UowDep, storage: StorageDep, config: ConfigDep) -> ImageService:
    return ImageService(uow, storage, config)


def get_user_service(uow: UowDep) -> UserService:
    return UserService(uow)


def get_stats_service(uow: UowDep) -> StatsService:
    return StatsService(uow)


def get_team_service(uow: UowDep) -> TeamService:
    return TeamService(uow)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
MeasurementServiceDep = Annotated[MeasurementService, Depends(get_measurement_service)]
ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]
TeamServiceDep = Annotated[TeamService, Depends(get_team_service)]


# ------------------------------------------------------------- yordamchilar


class Pagination:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Sahifa raqami")] = 1,
        size: Annotated[int, Query(ge=1, le=100, description="Sahifadagi yozuvlar soni")] = 20,
    ) -> None:
        self.page = page
        self.size = size


PaginationDep = Annotated[Pagination, Depends(Pagination)]


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
