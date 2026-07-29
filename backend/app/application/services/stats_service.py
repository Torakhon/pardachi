"""Dashboard statistikasi."""

from __future__ import annotations

from app.domain.models import User
from app.domain.repositories import UnitOfWork
from app.schemas.project import ProjectSummary
from app.schemas.stats import DashboardResponse, MeasurerStats


class StatsService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def dashboard(self, actor: User, recent_limit: int = 5) -> DashboardResponse:
        scope_id = None if actor.is_admin else actor.id
        stats = await self._uow.projects.stats(scope_id)
        recent = await self._uow.projects.recent(recent_limit, scope_id)

        return DashboardResponse(
            projects_total=stats.projects_total,
            projects_draft=stats.projects_draft,
            projects_in_progress=stats.projects_in_progress,
            projects_completed=stats.projects_completed,
            rooms_total=stats.rooms_total,
            items_total=stats.items_total,
            windows_total=stats.windows_total,
            doors_total=stats.doors_total,
            photos_total=stats.photos_total,
            users_total=stats.users_total if actor.is_admin else 0,
            recent_projects=[ProjectSummary.model_validate(project) for project in recent],
            per_measurer=[MeasurerStats(**row) for row in stats.per_measurer] if actor.is_admin else [],
        )
