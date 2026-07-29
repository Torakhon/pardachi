"""Loyiha (obyekt) sxemalari."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, computed_field, field_validator

from app.domain.enums import LocationSource, ProjectStatus
from app.schemas.common import ORMModel, PhoneMixin
from app.schemas.room import RoomCreate, RoomRead
from app.schemas.user import UserShort


class LocationBase(ORMModel):
    latitude: Annotated[Decimal, Field(ge=-90, le=90, decimal_places=6)]
    longitude: Annotated[Decimal, Field(ge=-180, le=180, decimal_places=6)]
    accuracy_m: Annotated[Decimal | None, Field(default=None, ge=0, le=100000, decimal_places=2)] = None
    source: LocationSource = LocationSource.BROWSER


class LocationCreate(LocationBase):
    captured_at: datetime | None = None


class LocationRead(LocationBase):
    id: uuid.UUID
    project_id: uuid.UUID
    captured_at: datetime

    @computed_field(description="Google Maps havolasi")  # type: ignore[prop-decorator]
    @property
    def maps_url(self) -> str:
        return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"


class ProjectBase(PhoneMixin, ORMModel):
    name: Annotated[str, Field(min_length=2, max_length=160)]
    order_number: Annotated[str, Field(min_length=1, max_length=64)]
    customer_name: Annotated[str, Field(min_length=2, max_length=160)]
    customer_phone: Annotated[str, Field(min_length=7, max_length=32)]
    address: Annotated[str, Field(default="", max_length=400)] = ""
    note: Annotated[str | None, Field(default=None, max_length=4000)] = None

    @field_validator("name", "order_number", "customer_name", "address")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("note")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ProjectCreate(ProjectBase):
    id: uuid.UUID | None = Field(
        default=None, description="Ixtiyoriy: mijoz yaratgan UUID (oflayn sinxronizatsiya)"
    )
    status: ProjectStatus = ProjectStatus.DRAFT
    location: LocationCreate | None = None
    rooms: list[RoomCreate] = Field(
        default_factory=list, description="Ixtiyoriy: obyekt bilan birga yaratiladigan xonalar"
    )


class ProjectUpdate(PhoneMixin, ORMModel):
    name: Annotated[str | None, Field(default=None, min_length=2, max_length=160)] = None
    order_number: Annotated[str | None, Field(default=None, min_length=1, max_length=64)] = None
    customer_name: Annotated[str | None, Field(default=None, min_length=2, max_length=160)] = None
    customer_phone: Annotated[str | None, Field(default=None, min_length=7, max_length=32)] = None
    address: Annotated[str | None, Field(default=None, max_length=400)] = None
    note: Annotated[str | None, Field(default=None, max_length=4000)] = None
    status: ProjectStatus | None = None
    location: LocationCreate | None = None


class ProjectStatusUpdate(ORMModel):
    status: ProjectStatus


class ProjectSummary(ORMModel):
    """Ro'yxatlarda ishlatiladigan qisqa ko'rinish."""

    id: uuid.UUID
    name: str
    order_number: str
    customer_name: str
    customer_phone: str
    address: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    creator: UserShort | None = None
    rooms_count: int = 0
    items_count: int = 0
    photos_count: int = 0
    location: LocationRead | None = None

    @computed_field(description="Holat nomi (o'zbekcha)")  # type: ignore[prop-decorator]
    @property
    def status_label(self) -> str:
        return ProjectStatus(self.status).label_uz


class ProjectRead(ProjectSummary):
    note: str | None = None
    rooms: list[RoomRead] = Field(default_factory=list)


class ProjectFilterParams(BaseModel):
    """Swagger hujjatida ko'rinadigan filtr parametrlari."""

    search: str | None = Field(default=None, description="Obyekt nomi, mijoz, buyurtma raqami yoki telefon")
    status: ProjectStatus | None = Field(default=None, description="Holat bo'yicha filtr")
    measurer_id: uuid.UUID | None = Field(default=None, description="O'lchovchi bo'yicha filtr")
    date_from: date | None = Field(default=None, description="Sanadan (YYYY-MM-DD)")
    date_to: date | None = Field(default=None, description="Sanagacha (YYYY-MM-DD)")
