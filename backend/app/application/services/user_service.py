"""Foydalanuvchilarni boshqarish (admin uchun)."""

from __future__ import annotations

import uuid

from app.application.permissions import ensure_admin
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.enums import AuditAction, UserRole
from app.domain.models import User
from app.domain.repositories import Page, UnitOfWork, UserFilters
from app.schemas.user import UserCreate, UserSelfUpdate, UserUpdate


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list(
        self,
        actor: User,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Page[User]:
        ensure_admin(actor)
        filters = UserFilters(search=search, role=role, is_active=is_active)
        return await self._uow.users.list(filters, page, size)

    async def list_measurers(self, actor: User) -> list[User]:
        """Filtrlar uchun o'lchovchilar ro'yxati."""
        ensure_admin(actor)
        users = await self._uow.users.list_all()
        return [user for user in users if user.is_active]

    async def get(self, user_id: uuid.UUID, actor: User) -> User:
        if actor.id != user_id:
            ensure_admin(actor)
        user = await self._uow.users.get(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi.")
        return user

    async def create(self, payload: UserCreate, actor: User) -> User:
        ensure_admin(actor)
        if payload.telegram_id is not None:
            existing = await self._uow.users.get_by_telegram_id(payload.telegram_id)
            if existing is not None:
                raise ConflictError("Bu Telegram ID bilan foydalanuvchi allaqachon mavjud.")

        user = User(
            telegram_id=payload.telegram_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            username=payload.username,
            phone=payload.phone,
            role=payload.role,
            is_active=payload.is_active,
        )
        await self._uow.users.add(user)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=str(user.id),
            payload={"role": user.role.value},
        )
        await self._uow.commit()
        return user

    async def update(self, user_id: uuid.UUID, payload: UserUpdate, actor: User) -> User:
        ensure_admin(actor)
        user = await self._uow.users.get(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi.")

        data = payload.model_dump(exclude_unset=True)
        if user.id == actor.id:
            if data.get("role") is not None and UserRole(data["role"]) is not UserRole.ADMIN:
                raise ValidationError("O'zingizning admin rolingizni o'zgartira olmaysiz.")
            if data.get("is_active") is False:
                raise ValidationError("O'zingizni bloklay olmaysiz.")

        for field, value in data.items():
            setattr(user, field, value)

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=str(user.id),
            payload={"fields": sorted(data.keys())},
        )
        await self._uow.commit()
        return user

    async def update_self(self, payload: UserSelfUpdate, actor: User) -> User:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(actor, field, value)
        await self._uow.commit()
        return actor

    async def delete(self, user_id: uuid.UUID, actor: User) -> None:
        ensure_admin(actor)
        if user_id == actor.id:
            raise ValidationError("O'z hisobingizni o'chira olmaysiz.")
        user = await self._uow.users.get(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi.")

        # Obyektlari bor foydalanuvchi o'chirilmaydi — faqat bloklanadi.
        projects = await self._uow.projects.recent(1, user.id)
        if projects:
            raise ConflictError("Bu foydalanuvchida obyektlar mavjud. Uni o'chirish o'rniga bloklang.")

        await self._uow.users.delete(user)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=str(user_id),
            payload=None,
        )
        await self._uow.commit()
