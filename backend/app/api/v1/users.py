"""Foydalanuvchilarni boshqarish (administrator)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminUser, CurrentUser, PaginationDep, UserServiceDep
from app.domain.enums import UserRole
from app.schemas.common import MessageResponse, PageMeta, PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserShort, UserUpdate

router = APIRouter(prefix="/users", tags=["Foydalanuvchilar"])

UserId = Annotated[uuid.UUID, Path(description="Foydalanuvchi identifikatori")]


@router.get(
    "",
    response_model=PaginatedResponse[UserRead],
    summary="Foydalanuvchilar ro'yxati (admin)",
)
async def list_users(
    admin: AdminUser,
    service: UserServiceDep,
    pagination: PaginationDep,
    search: Annotated[str | None, Query(max_length=120, description="Ism, username yoki telefon")] = None,
    role: Annotated[UserRole | None, Query(description="Rol bo'yicha filtr")] = None,
    is_active: Annotated[bool | None, Query(description="Faollik bo'yicha filtr")] = None,
    team_id: Annotated[uuid.UUID | None, Query(description="Jamoa bo'yicha filtr")] = None,
    without_team: Annotated[bool, Query(description="Faqat jamoasi yo'qlar")] = False,
) -> PaginatedResponse[UserRead]:
    page = await service.list(
        admin,
        search=search,
        role=role,
        team_id=team_id,
        without_team=without_team,
        is_active=is_active,
        page=pagination.page,
        size=pagination.size,
    )
    return PaginatedResponse[UserRead](
        items=[UserRead.model_validate(user) for user in page.items],
        meta=PageMeta(total=page.total, page=page.page, size=page.size, pages=page.pages),
    )


@router.get(
    "/measurers",
    response_model=list[UserShort],
    summary="O'lchovchilar ro'yxati (filtrlar uchun)",
)
async def list_measurers(user: CurrentUser, service: UserServiceDep) -> list[UserShort]:
    users = await service.list_measurers(user)
    return [UserShort.model_validate(user) for user in users]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Foydalanuvchi qo'shish (admin)",
)
async def create_user(payload: UserCreate, admin: AdminUser, service: UserServiceDep) -> UserRead:
    user = await service.create(payload, admin)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead, summary="Foydalanuvchi ma'lumoti")
async def get_user(user_id: UserId, admin: AdminUser, service: UserServiceDep) -> UserRead:
    user = await service.get(user_id, admin)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead, summary="Foydalanuvchini tahrirlash (admin)")
async def update_user(
    user_id: UserId,
    payload: UserUpdate,
    admin: AdminUser,
    service: UserServiceDep,
) -> UserRead:
    user = await service.update(user_id, payload, admin)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse, summary="Foydalanuvchini o'chirish (admin)")
async def delete_user(user_id: UserId, admin: AdminUser, service: UserServiceDep) -> MessageResponse:
    await service.delete(user_id, admin)
    return MessageResponse(message="Foydalanuvchi o'chirildi.")
