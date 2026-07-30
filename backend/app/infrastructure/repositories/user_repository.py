"""SQLAlchemy asosidagi foydalanuvchi repozitoriysi."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import User
from app.domain.repositories import Page, UserFilters, UserRepository

_ORDER_FIELDS = {
    "created_at": User.created_at,
    "first_name": User.first_name,
    "last_login_at": User.last_login_at,
    "role": User.role,
}


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, filters: UserFilters, page: int, size: int) -> Page[User]:
        stmt = select(User)
        conditions = []
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            conditions.append(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.username.ilike(pattern),
                    User.phone.ilike(pattern),
                )
            )
        if filters.role is not None:
            conditions.append(User.role == filters.role)
        if filters.is_active is not None:
            conditions.append(User.is_active.is_(filters.is_active))
        if filters.team_id is not None:
            conditions.append(User.team_id == filters.team_id)
        if filters.without_team:
            conditions.append(User.team_id.is_(None))
        if conditions:
            stmt = stmt.where(*conditions)

        total = await self._session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))

        stmt = stmt.order_by(_build_order(filters.order_by)).offset((page - 1) * size).limit(size)
        rows = list((await self._session.execute(stmt)).scalars().all())
        return Page(items=rows, total=int(total or 0), page=page, size=size)

    async def list_all(self) -> list[User]:
        stmt = select(User).order_by(User.first_name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)

    async def count(self) -> int:
        return int(await self._session.scalar(select(func.count(User.id))) or 0)


def _build_order(order_by: str):
    desc = order_by.startswith("-")
    field = _ORDER_FIELDS.get(order_by.lstrip("-"), User.created_at)
    return field.desc() if desc else field.asc()
