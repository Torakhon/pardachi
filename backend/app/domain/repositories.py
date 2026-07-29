"""Repozitoriy interfeyslari (abstraksiyalar).

Servis qatlami faqat shu interfeyslarga bog'lanadi; SQLAlchemy implementatsiyasi
`app/infrastructure/repositories` ichida joylashgan. Bu Dependency Inversion
tamoyilini ta'minlaydi va testlarda soxta (fake) repozitoriylardan foydalanish
imkonini beradi.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain.enums import AuditAction, ProjectStatus, UserRole
from app.domain.models import (
    AuditLog,
    MeasurementItem,
    Project,
    ProjectLocation,
    Room,
    RoomImage,
    User,
)


@dataclass
class Page[T]:
    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, (self.total + self.size - 1) // self.size) if self.size else 1


@dataclass(slots=True)
class ProjectFilters:
    search: str | None = None
    status: ProjectStatus | None = None
    created_by_id: uuid.UUID | None = None
    date_from: date | None = None
    date_to: date | None = None
    include_deleted: bool = False
    order_by: str = "-created_at"


@dataclass(slots=True)
class UserFilters:
    search: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    order_by: str = "-created_at"


@dataclass(slots=True)
class DashboardStats:
    projects_total: int = 0
    projects_draft: int = 0
    projects_in_progress: int = 0
    projects_completed: int = 0
    rooms_total: int = 0
    items_total: int = 0
    windows_total: int = 0
    doors_total: int = 0
    users_total: int = 0
    photos_total: int = 0
    per_measurer: list[dict[str, Any]] = field(default_factory=list)


class UserRepository(ABC):
    @abstractmethod
    async def get(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> User | None: ...

    @abstractmethod
    async def list(self, filters: UserFilters, page: int, size: int) -> Page[User]: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...

    @abstractmethod
    async def add(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user: User) -> None: ...

    @abstractmethod
    async def count(self) -> int: ...


class ProjectRepository(ABC):
    @abstractmethod
    async def get(self, project_id: uuid.UUID, *, include_deleted: bool = False) -> Project | None: ...

    @abstractmethod
    async def get_by_order_number(self, order_number: str) -> Project | None: ...

    @abstractmethod
    async def list(self, filters: ProjectFilters, page: int, size: int) -> Page[Project]: ...

    @abstractmethod
    async def recent(self, limit: int, created_by_id: uuid.UUID | None = None) -> list[Project]: ...

    @abstractmethod
    async def add(self, project: Project) -> Project: ...

    @abstractmethod
    async def delete(self, project: Project) -> None: ...

    @abstractmethod
    async def stats(self, created_by_id: uuid.UUID | None = None) -> DashboardStats: ...


class RoomRepository(ABC):
    @abstractmethod
    async def get(self, room_id: uuid.UUID) -> Room | None: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[Room]: ...

    @abstractmethod
    async def add(self, room: Room) -> Room: ...

    @abstractmethod
    async def delete(self, room: Room) -> None: ...

    @abstractmethod
    async def next_sort_order(self, project_id: uuid.UUID) -> int: ...


class MeasurementItemRepository(ABC):
    @abstractmethod
    async def get(self, item_id: uuid.UUID) -> MeasurementItem | None: ...

    @abstractmethod
    async def list_by_room(self, room_id: uuid.UUID) -> list[MeasurementItem]: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[MeasurementItem]: ...

    @abstractmethod
    async def add(self, item: MeasurementItem) -> MeasurementItem: ...

    @abstractmethod
    async def delete(self, item: MeasurementItem) -> None: ...

    @abstractmethod
    async def next_sort_order(self, room_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def count_by_type(self, room_id: uuid.UUID, item_type: str) -> int: ...


class RoomImageRepository(ABC):
    @abstractmethod
    async def get_by_room(self, room_id: uuid.UUID) -> RoomImage | None: ...

    @abstractmethod
    async def add(self, image: RoomImage) -> RoomImage: ...

    @abstractmethod
    async def delete(self, image: RoomImage) -> None: ...


class ProjectLocationRepository(ABC):
    @abstractmethod
    async def get_by_project(self, project_id: uuid.UUID) -> ProjectLocation | None: ...

    @abstractmethod
    async def add(self, location: ProjectLocation) -> ProjectLocation: ...

    @abstractmethod
    async def delete(self, location: ProjectLocation) -> None: ...


class AuditLogRepository(ABC):
    @abstractmethod
    async def add(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: str | None,
        payload: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog: ...

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[AuditLog]: ...


class UnitOfWork(ABC):
    """Tranzaksiya chegarasi va repozitoriylar to'plami."""

    users: UserRepository
    projects: ProjectRepository
    rooms: RoomRepository
    items: MeasurementItemRepository
    images: RoomImageRepository
    locations: ProjectLocationRepository
    audit: AuditLogRepository

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...

    @abstractmethod
    async def refresh(self, instance: Any) -> None: ...
