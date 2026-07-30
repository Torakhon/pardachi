"""Dashboard statistikasi."""

from __future__ import annotations

from app.domain.models import User
from app.domain.repositories import ProjectScope, UnitOfWork
from app.schemas.project import ProjectSummary
from app.schemas.stats import DashboardResponse, MeasurerStats, TeamStatsRow


class StatsService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def dashboard(self, actor: User, recent_limit: int = 5) -> DashboardResponse:
        scope = ProjectScope(all_teams=True) if actor.is_admin else ProjectScope(team_id=actor.team_id)
        stats = await self._uow.projects.stats(scope)
        recent = await self._uow.projects.recent(recent_limit, scope)

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
            users_total=stats.users_total,
            teams_total=stats.teams_total,
            recent_projects=[ProjectSummary.model_validate(project) for project in recent],
            per_measurer=[MeasurerStats(**row) for row in stats.per_measurer],
            per_team=[TeamStatsRow(**row) for row in stats.per_team],
        )
