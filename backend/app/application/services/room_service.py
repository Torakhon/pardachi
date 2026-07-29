"""Xona biznes logikasi."""

from __future__ import annotations

import uuid

from app.application.permissions import ensure_can_edit_project, ensure_can_view_project
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums import AuditAction, ProjectStatus
from app.domain.models import Project, Room, User
from app.domain.repositories import UnitOfWork
from app.schemas.room import RoomCreate, RoomUpdate


class RoomService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_by_project(self, project_id: uuid.UUID, actor: User) -> list[Room]:
        project = await self._require_project(project_id)
        ensure_can_view_project(actor, project)
        return await self._uow.rooms.list_by_project(project_id)

    async def get(self, room_id: uuid.UUID, actor: User) -> Room:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_view_project(actor, project)
        return room

    async def create(self, project_id: uuid.UUID, payload: RoomCreate, actor: User) -> Room:
        project = await self._require_project(project_id)
        ensure_can_edit_project(actor, project)

        if payload.id is not None:
            existing = await self._uow.rooms.get(payload.id)
            if existing is not None:
                return existing  # oflayn sinxronizatsiya idempotentligi

        sort_order = (
            payload.sort_order
            if payload.sort_order is not None
            else await self._uow.rooms.next_sort_order(project_id)
        )
        room = Room(
            id=payload.id or uuid.uuid4(),
            project_id=project_id,
            name=payload.name,
            room_type=payload.room_type,
            note=payload.note,
            sort_order=sort_order,
        )
        from app.application.services.measurement_service import build_item  # lokal import: sikl oldini olish

        room.items = [
            build_item(room.id, item_payload, index)
            for index, item_payload in enumerate(payload.items, start=1)
        ]
        await self._uow.rooms.add(room)

        self._touch_project(project, actor)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.CREATE,
            entity_type="room",
            entity_id=str(room.id),
            payload={"project_id": str(project_id), "name": room.name},
        )
        await self._uow.commit()
        refreshed = await self._uow.rooms.get(room.id)
        assert refreshed is not None
        return refreshed

    async def update(self, room_id: uuid.UUID, payload: RoomUpdate, actor: User) -> Room:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(room, field, value)

        self._touch_project(project, actor)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="room",
            entity_id=str(room.id),
            payload={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
        )
        await self._uow.commit()
        return room

    async def delete(self, room_id: uuid.UUID, actor: User) -> None:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        image = await self._uow.images.get_by_room(room_id)
        storage_key = image.storage_key if image else None

        await self._uow.rooms.delete(room)
        self._touch_project(project, actor)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.DELETE,
            entity_type="room",
            entity_id=str(room_id),
            payload={"project_id": str(project.id), "storage_key": storage_key},
        )
        await self._uow.commit()

    async def reorder(self, project_id: uuid.UUID, room_ids: list[uuid.UUID], actor: User) -> list[Room]:
        project = await self._require_project(project_id)
        ensure_can_edit_project(actor, project)

        rooms = {room.id: room for room in await self._uow.rooms.list_by_project(project_id)}
        unknown = [str(room_id) for room_id in room_ids if room_id not in rooms]
        if unknown:
            raise ValidationError("Ba'zi xonalar ushbu obyektga tegishli emas.", details={"ids": unknown})

        for index, room_id in enumerate(room_ids, start=1):
            rooms[room_id].sort_order = index

        self._touch_project(project, actor)
        await self._uow.commit()
        return await self._uow.rooms.list_by_project(project_id)

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

    @staticmethod
    def _touch_project(project: Project, actor: User) -> None:
        project.updated_by_id = actor.id
        if project.status is ProjectStatus.DRAFT:
            project.status = ProjectStatus.IN_PROGRESS
