"""Xona, o'lchov elementi va rasm repozitoriylari."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import MeasurementItem, ProjectLocation, Room, RoomImage
from app.domain.repositories import (
    MeasurementItemRepository,
    ProjectLocationRepository,
    RoomImageRepository,
    RoomRepository,
)


class SqlAlchemyRoomRepository(RoomRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, room_id: uuid.UUID) -> Room | None:
        return await self._session.get(Room, room_id, populate_existing=True)

    async def list_by_project(self, project_id: uuid.UUID) -> list[Room]:
        stmt = select(Room).where(Room.project_id == project_id).order_by(Room.sort_order, Room.created_at)
        return list((await self._session.execute(stmt)).unique().scalars().all())

    async def add(self, room: Room) -> Room:
        self._session.add(room)
        await self._session.flush()
        return room

    async def delete(self, room: Room) -> None:
        await self._session.delete(room)

    async def next_sort_order(self, project_id: uuid.UUID) -> int:
        current = await self._session.scalar(
            select(func.max(Room.sort_order)).where(Room.project_id == project_id)
        )
        return int(current or 0) + 1


class SqlAlchemyMeasurementItemRepository(MeasurementItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, item_id: uuid.UUID) -> MeasurementItem | None:
        return await self._session.get(MeasurementItem, item_id, populate_existing=True)

    async def list_by_room(self, room_id: uuid.UUID) -> list[MeasurementItem]:
        stmt = (
            select(MeasurementItem)
            .where(MeasurementItem.room_id == room_id)
            .order_by(MeasurementItem.sort_order, MeasurementItem.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_project(self, project_id: uuid.UUID) -> list[MeasurementItem]:
        stmt = (
            select(MeasurementItem)
            .join(Room, Room.id == MeasurementItem.room_id)
            .where(Room.project_id == project_id)
            .order_by(Room.sort_order, MeasurementItem.sort_order)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def add(self, item: MeasurementItem) -> MeasurementItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def delete(self, item: MeasurementItem) -> None:
        await self._session.delete(item)

    async def next_sort_order(self, room_id: uuid.UUID) -> int:
        current = await self._session.scalar(
            select(func.max(MeasurementItem.sort_order)).where(MeasurementItem.room_id == room_id)
        )
        return int(current or 0) + 1

    async def count_by_type(self, room_id: uuid.UUID, item_type: str) -> int:
        value = await self._session.scalar(
            select(func.count(MeasurementItem.id)).where(
                MeasurementItem.room_id == room_id,
                MeasurementItem.item_type == item_type,
            )
        )
        return int(value or 0)


class SqlAlchemyRoomImageRepository(RoomImageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_room(self, room_id: uuid.UUID) -> RoomImage | None:
        stmt = select(RoomImage).where(RoomImage.room_id == room_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, image: RoomImage) -> RoomImage:
        self._session.add(image)
        await self._session.flush()
        return image

    async def delete(self, image: RoomImage) -> None:
        await self._session.delete(image)


class SqlAlchemyProjectLocationRepository(ProjectLocationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_project(self, project_id: uuid.UUID) -> ProjectLocation | None:
        stmt = select(ProjectLocation).where(ProjectLocation.project_id == project_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, location: ProjectLocation) -> ProjectLocation:
        self._session.add(location)
        await self._session.flush()
        return location

    async def delete(self, location: ProjectLocation) -> None:
        await self._session.delete(location)
