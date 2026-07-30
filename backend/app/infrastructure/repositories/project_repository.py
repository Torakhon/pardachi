"""SQLAlchemy asosidagi loyiha (obyekt) repozitoriysi."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MeasurementItemType, ProjectStatus
from app.domain.models import MeasurementItem, Project, Room, RoomImage, Team, User
from app.domain.repositories import (
    DashboardStats,
    Page,
    ProjectFilters,
    ProjectRepository,
    ProjectScope,
)

_ORDER_FIELDS = {
    "created_at": Project.created_at,
    "updated_at": Project.updated_at,
    "name": Project.name,
    "order_number": Project.order_number,
    "status": Project.status,
}


class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, project_id: uuid.UUID, *, include_deleted: bool = False) -> Project | None:
        # populate_existing=True — identity-map'dagi obyektning eager (selectin)
        # bog'lanishlari qayta yuklanadi, aks holda yangi yaratilgan obyektlarda
        # ular bo'sh qolib, seriyalash paytida lazy-load xatosi yuzaga keladi.
        project = await self._session.get(Project, project_id, populate_existing=True)
        if project is None:
            return None
        if project.deleted_at is not None and not include_deleted:
            return None
        return project

    async def get_by_order_number(self, order_number: str) -> Project | None:
        stmt = select(Project).where(func.lower(Project.order_number) == order_number.strip().lower())
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, filters: ProjectFilters, page: int, size: int) -> Page[Project]:
        stmt = self._apply_filters(select(Project), filters)

        total = await self._session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))

        stmt = stmt.order_by(_build_order(filters.order_by)).offset((page - 1) * size).limit(size)
        rows = list((await self._session.execute(stmt)).unique().scalars().all())
        return Page(items=rows, total=int(total or 0), page=page, size=size)

    async def recent(self, limit: int, scope: ProjectScope) -> list[Project]:
        if scope.is_empty:
            return []
        stmt = select(Project).where(Project.deleted_at.is_(None))
        if not scope.all_teams:
            stmt = stmt.where(Project.team_id == scope.team_id)
        stmt = stmt.order_by(Project.updated_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).unique().scalars().all())

    async def count_by_team(self, team_id: uuid.UUID) -> int:
        value = await self._session.scalar(
            select(func.count(Project.id)).where(Project.team_id == team_id, Project.deleted_at.is_(None))
        )
        return int(value or 0)

    async def first_by_creator(self, user_id: uuid.UUID) -> Project | None:
        stmt = select(Project).where(Project.created_by_id == user_id).limit(1)
        return (await self._session.execute(stmt)).unique().scalars().first()

    async def add(self, project: Project) -> Project:
        self._session.add(project)
        await self._session.flush()
        return project

    async def delete(self, project: Project) -> None:
        await self._session.delete(project)

    async def stats(self, scope: ProjectScope) -> DashboardStats:
        if scope.is_empty:
            return DashboardStats()

        base = select(Project).where(Project.deleted_at.is_(None))
        if not scope.all_teams:
            base = base.where(Project.team_id == scope.team_id)
        project_ids = base.with_only_columns(Project.id).scalar_subquery()

        status_rows = (
            await self._session.execute(
                select(Project.status, func.count(Project.id))
                .where(Project.id.in_(project_ids))
                .group_by(Project.status)
            )
        ).all()
        by_status = {status: int(count) for status, count in status_rows}

        rooms_total = int(
            await self._session.scalar(select(func.count(Room.id)).where(Room.project_id.in_(project_ids)))
            or 0
        )
        photos_total = int(
            await self._session.scalar(
                select(func.count(RoomImage.id))
                .join(Room, Room.id == RoomImage.room_id)
                .where(Room.project_id.in_(project_ids))
            )
            or 0
        )
        item_rows = (
            await self._session.execute(
                select(MeasurementItem.item_type, func.count(MeasurementItem.id))
                .join(Room, Room.id == MeasurementItem.room_id)
                .where(Room.project_id.in_(project_ids))
                .group_by(MeasurementItem.item_type)
            )
        ).all()
        by_type = {item_type: int(count) for item_type, count in item_rows}

        users_stmt = select(func.count(User.id))
        if not scope.all_teams:
            users_stmt = users_stmt.where(User.team_id == scope.team_id)
        users_total = int(await self._session.scalar(users_stmt) or 0)

        teams_total = int(
            await self._session.scalar(
                select(func.count(Team.id))
                if scope.all_teams
                else select(func.count(Team.id)).where(Team.id == scope.team_id)
            )
            or 0
        )

        per_team: list[dict[str, object]] = []
        if scope.all_teams:
            team_rows = (
                await self._session.execute(
                    select(
                        Team.id,
                        Team.name,
                        func.count(Project.id),
                        func.sum(case((Project.status == ProjectStatus.COMPLETED, 1), else_=0)),
                    )
                    .outerjoin(
                        Project,
                        (Project.team_id == Team.id) & (Project.deleted_at.is_(None)),
                    )
                    .group_by(Team.id, Team.name)
                    .order_by(func.count(Project.id).desc())
                )
            ).all()
            per_team = [
                {
                    "team_id": str(team_id),
                    "name": name,
                    "projects_count": int(count or 0),
                    "completed_count": int(completed or 0),
                }
                for team_id, name, count, completed in team_rows
            ]

        per_measurer: list[dict[str, object]] = []
        measurer_stmt = (
            select(
                User.id,
                User.first_name,
                User.last_name,
                func.count(Project.id),
                func.sum(case((Project.status == ProjectStatus.COMPLETED, 1), else_=0)),
            )
            .join(Project, Project.created_by_id == User.id)
            .where(Project.deleted_at.is_(None))
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(func.count(Project.id).desc())
        )
        if not scope.all_teams:
            measurer_stmt = measurer_stmt.where(Project.team_id == scope.team_id)
        rows = (await self._session.execute(measurer_stmt)).all()
        for user_id, first_name, last_name, count, completed in rows:
            per_measurer.append(
                {
                    "user_id": str(user_id),
                    "full_name": " ".join(p for p in [first_name, last_name] if p).strip(),
                    "projects_count": int(count or 0),
                    "completed_count": int(completed or 0),
                }
            )

        return DashboardStats(
            projects_total=sum(by_status.values()),
            projects_draft=by_status.get(ProjectStatus.DRAFT, 0),
            projects_in_progress=by_status.get(ProjectStatus.IN_PROGRESS, 0),
            projects_completed=by_status.get(ProjectStatus.COMPLETED, 0),
            rooms_total=rooms_total,
            items_total=sum(by_type.values()),
            windows_total=by_type.get(MeasurementItemType.WINDOW, 0),
            doors_total=by_type.get(MeasurementItemType.DOOR, 0),
            users_total=users_total,
            photos_total=photos_total,
            teams_total=teams_total,
            per_measurer=per_measurer,
            per_team=per_team,
        )

    def _apply_filters(self, stmt: Select[tuple[Project]], filters: ProjectFilters) -> Select[tuple[Project]]:
        conditions = []
        if not filters.include_deleted:
            conditions.append(Project.deleted_at.is_(None))
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            digits = "".join(ch for ch in filters.search if ch.isdigit())
            phone_pattern = f"%{digits}%" if digits else pattern
            conditions.append(
                or_(
                    Project.name.ilike(pattern),
                    Project.customer_name.ilike(pattern),
                    Project.order_number.ilike(pattern),
                    Project.customer_phone.ilike(phone_pattern),
                    Project.address.ilike(pattern),
                )
            )
        if filters.status is not None:
            conditions.append(Project.status == filters.status)
        if filters.created_by_id is not None:
            conditions.append(Project.created_by_id == filters.created_by_id)
        if filters.team_id is not None:
            conditions.append(Project.team_id == filters.team_id)
        if filters.date_from is not None:
            conditions.append(Project.created_at >= datetime.combine(filters.date_from, time.min, tzinfo=UTC))
        if filters.date_to is not None:
            conditions.append(Project.created_at <= datetime.combine(filters.date_to, time.max, tzinfo=UTC))
        return stmt.where(*conditions) if conditions else stmt


def _build_order(order_by: str):
    desc = order_by.startswith("-")
    field = _ORDER_FIELDS.get(order_by.lstrip("-"), Project.created_at)
    return field.desc() if desc else field.asc()
