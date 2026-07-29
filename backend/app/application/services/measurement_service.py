"""O'lchov elementlari (oyna / eshik) biznes logikasi."""

from __future__ import annotations

import uuid

from app.application.permissions import ensure_can_edit_project, ensure_can_view_project
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums import AuditAction, MeasurementItemType, ProjectStatus
from app.domain.models import MeasurementItem, Project, Room, User
from app.domain.repositories import UnitOfWork
from app.schemas.measurement import MeasurementItemCreate, MeasurementItemUpdate


def build_item(room_id: uuid.UUID, payload: MeasurementItemCreate, sort_order: int) -> MeasurementItem:
    """`MeasurementItemCreate` sxemasidan domen obyektini yasaydi."""
    return MeasurementItem(
        id=payload.id or uuid.uuid4(),
        room_id=room_id,
        name=payload.name,
        item_type=payload.item_type,
        quantity=payload.quantity,
        width_cm=payload.width_cm,
        height_cm=payload.height_cm,
        curtain_width_cm=payload.curtain_width_cm,
        curtain_height_cm=payload.curtain_height_cm,
        cornice_width_cm=payload.cornice_width_cm,
        cornice_height_cm=payload.cornice_height_cm,
        fabric_type=payload.fabric_type,
        curtain_model=payload.curtain_model,
        fabric_color=payload.fabric_color,
        notes=payload.notes,
        sort_order=payload.sort_order if payload.sort_order is not None else sort_order,
    )


class MeasurementService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_by_room(self, room_id: uuid.UUID, actor: User) -> list[MeasurementItem]:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_view_project(actor, project)
        return await self._uow.items.list_by_room(room_id)

    async def list_by_project(self, project_id: uuid.UUID, actor: User) -> list[MeasurementItem]:
        project = await self._require_project(project_id)
        ensure_can_view_project(actor, project)
        return await self._uow.items.list_by_project(project_id)

    async def get(self, item_id: uuid.UUID, actor: User) -> MeasurementItem:
        item = await self._require_item(item_id)
        room = await self._require_room(item.room_id)
        project = await self._require_project(room.project_id)
        ensure_can_view_project(actor, project)
        return item

    async def suggest_name(self, room_id: uuid.UUID, item_type: MeasurementItemType) -> str:
        """Keyingi element uchun nom taklif qiladi: «Oyna 1», «Eshik 2» ..."""
        count = await self._uow.items.count_by_type(room_id, item_type.value)
        return f"{item_type.label_uz} {count + 1}"

    async def create(
        self, room_id: uuid.UUID, payload: MeasurementItemCreate, actor: User
    ) -> MeasurementItem:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        if payload.id is not None:
            existing = await self._uow.items.get(payload.id)
            if existing is not None:
                return existing  # oflayn sinxronizatsiya idempotentligi

        sort_order = (
            payload.sort_order
            if payload.sort_order is not None
            else await self._uow.items.next_sort_order(room_id)
        )
        item = build_item(room_id, payload, sort_order)
        await self._uow.items.add(item)

        self._touch_project(project, actor)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.CREATE,
            entity_type="measurement_item",
            entity_id=str(item.id),
            payload={"room_id": str(room_id), "type": item.item_type.value, "name": item.name},
        )
        await self._uow.commit()
        return item

    async def update(
        self, item_id: uuid.UUID, payload: MeasurementItemUpdate, actor: User
    ) -> MeasurementItem:
        item = await self._require_item(item_id)
        room = await self._require_room(item.room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)

        self._touch_project(project, actor)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="measurement_item",
            entity_id=str(item.id),
            payload={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
        )
        await self._uow.commit()
        return item

    async def delete(self, item_id: uuid.UUID, actor: User) -> None:
        item = await self._require_item(item_id)
        room = await self._require_room(item.room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        await self._uow.items.delete(item)
        self._touch_project(project, actor)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.DELETE,
            entity_type="measurement_item",
            entity_id=str(item_id),
            payload={"room_id": str(room.id)},
        )
        await self._uow.commit()

    async def reorder(
        self, room_id: uuid.UUID, item_ids: list[uuid.UUID], actor: User
    ) -> list[MeasurementItem]:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        items = {item.id: item for item in await self._uow.items.list_by_room(room_id)}
        unknown = [str(item_id) for item_id in item_ids if item_id not in items]
        if unknown:
            raise ValidationError("Ba'zi o'lchovlar ushbu xonaga tegishli emas.", details={"ids": unknown})

        for index, item_id in enumerate(item_ids, start=1):
            items[item_id].sort_order = index

        await self._uow.commit()
        return await self._uow.items.list_by_room(room_id)

    # ------------------------------------------------------------ internal

    async def _require_project(self, project_id: uuid.UUID) -> Project:
        project = await self._uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        return project

    async def _require_room(self, room_id: uuid.UUID) -> Room:
        room = await self._uow.rooms.get(room_id)
        if room is None:
            raise NotFoundError("Xona topilmadi.")
        return room

    async def _require_item(self, item_id: uuid.UUID) -> MeasurementItem:
        item = await self._uow.items.get(item_id)
        if item is None:
            raise NotFoundError("O'lchov topilmadi.")
        return item

    @staticmethod
    def _touch_project(project: Project, actor: User) -> None:
        project.updated_by_id = actor.id
        if project.status is ProjectStatus.DRAFT:
            project.status = ProjectStatus.IN_PROGRESS
