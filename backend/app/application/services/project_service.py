"""Loyiha (obyekt) biznes logikasi."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.application.permissions import (
    ensure_admin,
    ensure_can_create_project,
    ensure_can_delete_project,
    ensure_can_edit_project,
    ensure_can_view_project,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger, log_extra
from app.domain.enums import AuditAction, ProjectStatus
from app.domain.models import MeasurementItem, Project, ProjectLocation, Room, User
from app.domain.repositories import (
    DashboardStats,
    Page,
    ProjectFilters,
    ProjectScope,
    UnitOfWork,
)
from app.schemas.project import LocationCreate, ProjectCreate, ProjectUpdate
from app.schemas.room import RoomCreate

logger = get_logger(__name__)


class ProjectService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    # ---------------------------------------------------------------- read

    async def get(self, project_id: uuid.UUID, actor: User) -> Project:
        project = await self._uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        ensure_can_view_project(actor, project)
        return project

    async def list(
        self,
        actor: User,
        *,
        search: str | None = None,
        status: ProjectStatus | None = None,
        measurer_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        order_by: str = "-created_at",
        page: int = 1,
        size: int = 20,
    ) -> Page[Project]:
        scope = self._scope(actor)
        if scope.is_empty:
            # Jamoaga biriktirilmagan foydalanuvchi hech narsa ko'rmaydi.
            return Page(items=[], total=0, page=page, size=size)

        filters = ProjectFilters(
            search=search,
            status=status,
            created_by_id=measurer_id,
            # Administrator jamoani tanlashi mumkin; boshqalar uchun o'z jamoasi majburiy.
            team_id=team_id if scope.all_teams else scope.team_id,
            date_from=date_from,
            date_to=date_to,
            order_by=order_by,
        )
        return await self._uow.projects.list(filters, page, size)

    @staticmethod
    def _scope(actor: User) -> ProjectScope:
        if actor.is_admin:
            return ProjectScope(all_teams=True)
        return ProjectScope(team_id=actor.team_id)

    async def recent(self, actor: User, limit: int = 5) -> list[Project]:
        return await self._uow.projects.recent(limit, self._scope(actor))

    async def stats(self, actor: User) -> DashboardStats:
        return await self._uow.projects.stats(self._scope(actor))

    async def next_order_number(self) -> str:
        """`OB-YYYYMMDD-NNN` ko'rinishidagi bo'sh buyurtma raqamini qaytaradi."""
        today = datetime.now(UTC).date()
        prefix = f"OB-{today:%Y%m%d}"
        for counter in range(1, 1000):
            candidate = f"{prefix}-{counter:03d}"
            if await self._uow.projects.get_by_order_number(candidate) is None:
                return candidate
        return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"

    # --------------------------------------------------------------- write

    async def create(self, payload: ProjectCreate, actor: User) -> Project:
        ensure_can_create_project(actor)
        team_id = await self._resolve_team_for_create(actor)

        if payload.id is not None:
            existing = await self._uow.projects.get(payload.id, include_deleted=True)
            if existing is not None:
                # Oflayn sinxronizatsiya: bir xil so'rov ikki marta kelsa yangi yozuv yaratilmaydi.
                ensure_can_view_project(actor, existing)
                return existing

        await self._ensure_unique_order_number(payload.order_number)

        project = Project(
            id=payload.id or uuid.uuid4(),
            team_id=team_id,
            name=payload.name,
            order_number=payload.order_number,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            address=payload.address,
            note=payload.note,
            status=payload.status,
            created_by_id=actor.id,
            updated_by_id=actor.id,
        )
        if payload.status is ProjectStatus.COMPLETED:
            project.completed_at = datetime.now(UTC)

        # Bog'liq yozuvlar obyekt sessiyaga qo'shilishidan OLDIN biriktiriladi:
        # flush'dan keyin bo'sh kolleksiyaga murojaat qilish lazy-load chaqiradi.
        if payload.location is not None:
            project.location = self._build_location(project.id, payload.location)
        project.rooms = [
            self._build_room(project.id, room_payload, index)
            for index, room_payload in enumerate(payload.rooms, start=1)
        ]

        await self._uow.projects.add(project)

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.CREATE,
            entity_type="project",
            entity_id=str(project.id),
            payload={
                "name": project.name,
                "order_number": project.order_number,
                "team_id": str(team_id),
            },
        )
        await self._uow.commit()
        logger.info("Obyekt yaratildi", extra=log_extra(project_id=str(project.id)))
        return await self._reload(project.id)

    async def update(self, project_id: uuid.UUID, payload: ProjectUpdate, actor: User) -> Project:
        project = await self._uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        ensure_can_edit_project(actor, project)

        data = payload.model_dump(exclude_unset=True, exclude={"location"})

        new_order_number = data.pop("order_number", None)
        if new_order_number and new_order_number != project.order_number:
            await self._ensure_unique_order_number(new_order_number, exclude_id=project.id)
            project.order_number = new_order_number

        new_status = data.pop("status", None)
        if new_status is not None:
            self._apply_status(project, ProjectStatus(new_status))

        for field, value in data.items():
            setattr(project, field, value)

        if payload.location is not None:
            await self._upsert_location(project, payload.location)

        project.updated_by_id = actor.id

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="project",
            entity_id=str(project.id),
            payload={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
        )
        await self._uow.commit()
        return await self._reload(project.id)

    async def change_status(self, project_id: uuid.UUID, status: ProjectStatus, actor: User) -> Project:
        project = await self._uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        ensure_can_edit_project(actor, project)

        if status is ProjectStatus.COMPLETED:
            self._ensure_completable(project)

        self._apply_status(project, status)
        project.updated_by_id = actor.id

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.STATUS_CHANGE,
            entity_type="project",
            entity_id=str(project.id),
            payload={"status": status.value},
        )
        await self._uow.commit()
        return await self._reload(project.id)

    async def delete(self, project_id: uuid.UUID, actor: User, *, hard: bool = False) -> None:
        project = await self._uow.projects.get(project_id, include_deleted=True)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        ensure_can_delete_project(actor, project)
        if hard:
            ensure_admin(actor)

        if hard:
            await self._uow.projects.delete(project)
        else:
            project.deleted_at = datetime.now(UTC)

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.DELETE,
            entity_type="project",
            entity_id=str(project_id),
            payload={"hard": hard, "name": project.name},
        )
        await self._uow.commit()
        logger.info("Obyekt o'chirildi", extra=log_extra(project_id=str(project_id), hard=hard))

    async def restore(self, project_id: uuid.UUID, actor: User) -> Project:
        ensure_admin(actor)
        project = await self._uow.projects.get(project_id, include_deleted=True)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        project.deleted_at = None
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="project",
            entity_id=str(project_id),
            payload={"restored": True},
        )
        await self._uow.commit()
        return await self._reload(project_id)

    async def set_location(self, project_id: uuid.UUID, payload: LocationCreate, actor: User) -> Project:
        project = await self._uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        ensure_can_edit_project(actor, project)
        await self._upsert_location(project, payload)
        await self._uow.commit()
        return await self._reload(project_id)

    # ------------------------------------------------------------ internal

    async def _resolve_team_for_create(self, actor: User) -> uuid.UUID:
        """Yangi obyekt qaysi jamoaga tegishli bo'lishini aniqlaydi."""
        if actor.team_id is not None:
            return actor.team_id
        # Administratorda jamoa ko'rsatilmagan bo'lsa — birinchi faol jamoaga yoziladi.
        teams = await self._uow.teams.list(only_active=True)
        if not teams:
            raise ValidationError(
                "Avval kamida bitta jamoa yarating (Jamoalar bo'limi), so'ng obyekt qo'shing."
            )
        return teams[0].id

    async def _reload(self, project_id: uuid.UUID) -> Project:
        project = await self._uow.projects.get(project_id, include_deleted=True)
        if project is None:  # pragma: no cover - tranzaksiya buzilgan holat
            raise NotFoundError("Obyekt topilmadi.")
        return project

    async def _ensure_unique_order_number(
        self, order_number: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        existing = await self._uow.projects.get_by_order_number(order_number)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(f"«{order_number}» buyurtma raqami allaqachon mavjud.")

    def _ensure_completable(self, project: Project) -> None:
        if not project.rooms:
            raise ValidationError("Obyektni yakunlash uchun kamida bitta xona qo'shing.")
        rooms_without_photo = [room.name for room in project.rooms if room.image is None]
        if rooms_without_photo:
            raise ValidationError("Quyidagi xonalarga rasm yuklanmagan: " + ", ".join(rooms_without_photo))
        rooms_without_items = [room.name for room in project.rooms if not room.items]
        if rooms_without_items:
            raise ValidationError(
                "Quyidagi xonalarda o'lchov kiritilmagan: " + ", ".join(rooms_without_items)
            )

    def _apply_status(self, project: Project, status: ProjectStatus) -> None:
        project.status = status
        project.completed_at = datetime.now(UTC) if status is ProjectStatus.COMPLETED else None

    async def _upsert_location(self, project: Project, payload: LocationCreate) -> None:
        existing = await self._uow.locations.get_by_project(project.id)
        if existing is not None:
            await self._uow.locations.delete(existing)
            await self._uow.flush()
        location = self._build_location(project.id, payload)
        await self._uow.locations.add(location)
        project.location = location

    @staticmethod
    def _build_location(project_id: uuid.UUID, payload: LocationCreate) -> ProjectLocation:
        return ProjectLocation(
            project_id=project_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            source=payload.source,
            captured_at=payload.captured_at or datetime.now(UTC),
        )

    @staticmethod
    def _build_room(project_id: uuid.UUID, payload: RoomCreate, sort_order: int) -> Room:
        room = Room(
            id=payload.id or uuid.uuid4(),
            project_id=project_id,
            name=payload.name,
            room_type=payload.room_type,
            note=payload.note,
            sort_order=payload.sort_order if payload.sort_order is not None else sort_order,
        )
        for index, item in enumerate(payload.items, start=1):
            room.items.append(
                MeasurementItem(
                    id=item.id or uuid.uuid4(),
                    room_id=room.id,
                    name=item.name,
                    item_type=item.item_type,
                    quantity=item.quantity,
                    width_cm=item.width_cm,
                    height_cm=item.height_cm,
                    curtain_width_cm=item.curtain_width_cm,
                    curtain_height_cm=item.curtain_height_cm,
                    cornice_width_cm=item.cornice_width_cm,
                    cornice_height_cm=item.cornice_height_cm,
                    fabric_type=item.fabric_type,
                    curtain_model=item.curtain_model,
                    fabric_color=item.fabric_color,
                    notes=item.notes,
                    sort_order=item.sort_order if item.sort_order is not None else index,
                )
            )
        return room
