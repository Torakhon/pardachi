"""Statistika (dashboard) sxemalari."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.project import ProjectSummary


class MeasurerStats(BaseModel):
    user_id: uuid.UUID
    full_name: str
    projects_count: int
    completed_count: int


class TeamStatsRow(BaseModel):
    team_id: uuid.UUID
    name: str
    projects_count: int
    completed_count: int


class DashboardResponse(BaseModel):
    projects_total: int = Field(description="Jami obyektlar")
    projects_draft: int = Field(description="Yangi obyektlar")
    projects_in_progress: int = Field(description="Jarayondagi obyektlar")
    projects_completed: int = Field(description="Yakunlangan obyektlar")
    rooms_total: int = Field(description="Jami xonalar")
    items_total: int = Field(description="Jami o'lchovlar")
    windows_total: int = Field(description="Jami oynalar")
    doors_total: int = Field(description="Jami eshiklar")
    photos_total: int = Field(description="Jami rasmlar")
    users_total: int = Field(description="Jami foydalanuvchilar")
    teams_total: int = Field(default=0, description="Jami jamoalar")
    recent_projects: list[ProjectSummary] = Field(default_factory=list)
    per_measurer: list[MeasurerStats] = Field(default_factory=list)
    per_team: list[TeamStatsRow] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    database: str
