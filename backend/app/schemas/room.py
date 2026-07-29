"""Xona sxemalari."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, computed_field, field_validator

from app.domain.enums import RoomType
from app.schemas.common import ORMModel
from app.schemas.measurement import MeasurementItemCreate, MeasurementItemRead


class RoomImageRead(ORMModel):
    id: uuid.UUID
    room_id: uuid.UUID
    url: str
    content_type: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    created_at: datetime


class RoomBase(ORMModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    room_type: RoomType = RoomType.OTHER
    note: Annotated[str | None, Field(default=None, max_length=2000)] = None

    @field_validator("name", "note")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class RoomCreate(RoomBase):
    id: uuid.UUID | None = Field(
        default=None, description="Ixtiyoriy: mijoz yaratgan UUID (oflayn sinxronizatsiya)"
    )
    sort_order: Annotated[int | None, Field(default=None, ge=0, le=10000)] = None
    items: list[MeasurementItemCreate] = Field(
        default_factory=list,
        description="Ixtiyoriy: xona bilan birga yaratiladigan o'lchov elementlari",
    )


class RoomUpdate(ORMModel):
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=120)] = None
    room_type: RoomType | None = None
    note: Annotated[str | None, Field(default=None, max_length=2000)] = None
    sort_order: Annotated[int | None, Field(default=None, ge=0, le=10000)] = None


class RoomRead(RoomBase):
    id: uuid.UUID
    project_id: uuid.UUID
    sort_order: int
    created_at: datetime
    updated_at: datetime
    image: RoomImageRead | None = None
    items: list[MeasurementItemRead] = Field(default_factory=list)

    @computed_field(description="Xona turi nomi (o'zbekcha)")  # type: ignore[prop-decorator]
    @property
    def room_type_label(self) -> str:
        return RoomType(self.room_type).label_uz

    @computed_field(description="Oynalar soni")  # type: ignore[prop-decorator]
    @property
    def windows_count(self) -> int:
        return sum(1 for item in self.items if item.item_type == "window")

    @computed_field(description="Eshiklar soni")  # type: ignore[prop-decorator]
    @property
    def doors_count(self) -> int:
        return sum(1 for item in self.items if item.item_type == "door")

    @computed_field(description="Rasm yuklanganmi")  # type: ignore[prop-decorator]
    @property
    def has_image(self) -> bool:
        return self.image is not None


class RoomReorder(ORMModel):
    room_ids: list[uuid.UUID] = Field(min_length=1, description="Yangi tartibdagi xona ID lari")


class RoomTypeOption(ORMModel):
    value: RoomType
    label: str
