"""SQLAlchemy asosidagi jamoa repozitoriysi."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Team, User
from app.domain.repositories import TeamRepository


class SqlAlchemyTeamRepository(TeamRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, team_id: uuid.UUID) -> Team | None:
        return await self._session.get(Team, team_id, populate_existing=True)

    async def get_by_name(self, name: str) -> Team | None:
        stmt = select(Team).where(func.lower(Team.name) == name.strip().lower())
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, *, only_active: bool = False) -> list[Team]:
        stmt = select(Team).order_by(Team.name)
        if only_active:
            stmt = stmt.where(Team.is_active.is_(True))
        return list((await self._session.execute(stmt)).unique().scalars().all())

    async def add(self, team: Team) -> Team:
        self._session.add(team)
        await self._session.flush()
        return team

    async def delete(self, team: Team) -> None:
        await self._session.delete(team)

    async def members(self, team_id: uuid.UUID) -> list[User]:
        stmt = select(User).where(User.team_id == team_id).order_by(User.role, User.first_name)
        return list((await self._session.execute(stmt)).unique().scalars().all())

    async def count(self) -> int:
        return int(await self._session.scalar(select(func.count(Team.id))) or 0)
