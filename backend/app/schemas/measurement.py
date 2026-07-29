"""O'lchov elementi (oyna / eshik) sxemalari."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field, computed_field, field_validator, model_validator

from app.domain.enums import MeasurementItemType
from app.schemas.common import ORMModel

type Dimension = Annotated[Decimal, Field(gt=0, le=10000, decimal_places=2)]


def format_cm(value: Decimal) -> str:
    """`150.00` -> `150`, `150.50` -> `150.5` (ortiqcha nollarsiz ko'rinish)."""
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        normalized = normalized.to_integral_value()
    return f"{normalized:f}"


type OptionalDimension = Annotated[Decimal | None, Field(gt=0, le=10000, decimal_places=2)]
type ShortText = Annotated[str | None, Field(max_length=120)]


class MeasurementItemBase(ORMModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    item_type: MeasurementItemType
    quantity: Annotated[int, Field(default=1, ge=1, le=100)] = 1
    width_cm: Dimension
    height_cm: Dimension
    curtain_width_cm: OptionalDimension = None
    curtain_height_cm: OptionalDimension = None
    cornice_width_cm: OptionalDimension = None
    cornice_height_cm: OptionalDimension = None
    fabric_type: ShortText = None
    curtain_model: ShortText = None
    fabric_color: ShortText = None
    notes: Annotated[str | None, Field(default=None, max_length=2000)] = None

    @field_validator("name", "fabric_type", "curtain_model", "fabric_color", "notes")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class MeasurementItemCreate(MeasurementItemBase):
    id: uuid.UUID | None = Field(
        default=None,
        description="Ixtiyoriy: oflayn rejimda mijoz tomonidan yaratilgan UUID (idempotentlik uchun)",
    )
    sort_order: Annotated[int | None, Field(default=None, ge=0, le=10000)] = None

    @model_validator(mode="after")
    def _check_name(self) -> MeasurementItemCreate:
        if not self.name:
            raise ValueError("Nomini kiriting.")
        return self


class MeasurementItemUpdate(ORMModel):
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=120)] = None
    item_type: MeasurementItemType | None = None
    quantity: Annotated[int | None, Field(default=None, ge=1, le=100)] = None
    width_cm: Annotated[Decimal | None, Field(default=None, gt=0, le=10000, decimal_places=2)] = None
    height_cm: Annotated[Decimal | None, Field(default=None, gt=0, le=10000, decimal_places=2)] = None
    curtain_width_cm: OptionalDimension = None
    curtain_height_cm: OptionalDimension = None
    cornice_width_cm: OptionalDimension = None
    cornice_height_cm: OptionalDimension = None
    fabric_type: ShortText = None
    curtain_model: ShortText = None
    fabric_color: ShortText = None
    notes: Annotated[str | None, Field(default=None, max_length=2000)] = None
    sort_order: Annotated[int | None, Field(default=None, ge=0, le=10000)] = None


class MeasurementItemRead(MeasurementItemBase):
    id: uuid.UUID
    room_id: uuid.UUID
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @computed_field(description="Tur nomi (o'zbekcha)")  # type: ignore[prop-decorator]
    @property
    def type_label(self) -> str:
        return MeasurementItemType(self.item_type).label_uz

    @computed_field(description="O'lcham matni, masalan: 150 × 220 sm")  # type: ignore[prop-decorator]
    @property
    def size_label(self) -> str:
        return f"{format_cm(self.width_cm)} × {format_cm(self.height_cm)} sm"

    @computed_field(description="Yuza (m²)")  # type: ignore[prop-decorator]
    @property
    def area_m2(self) -> float:
        return round(float(self.width_cm) * float(self.height_cm) / 10_000, 3)


class MeasurementItemReorder(ORMModel):
    item_ids: list[uuid.UUID] = Field(min_length=1, description="Yangi tartibdagi ID lar ro'yxati")
