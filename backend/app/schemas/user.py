"""Foydalanuvchi sxemalari."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, computed_field

from app.domain.enums import UserRole
from app.schemas.common import ORMModel, PhoneMixin


class TeamRef(ORMModel):
    """Foydalanuvchi javobida ko'rsatiladigan qisqa jamoa ma'lumoti."""

    id: uuid.UUID
    name: str
    is_active: bool = True


class UserRead(ORMModel):
    id: uuid.UUID
    telegram_id: int | None = None
    username: str | None = None
    first_name: str
    last_name: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    role: UserRole
    is_active: bool
    language_code: str
    team_id: uuid.UUID | None = None
    team: TeamRef | None = None
    last_login_at: datetime | None = None
    created_at: datetime

    @computed_field(description="To'liq ism")  # type: ignore[prop-decorator]
    @property
    def full_name(self) -> str:
        name = " ".join(p for p in [self.first_name or "", self.last_name or ""] if p).strip()
        return name or (self.username or "Foydalanuvchi")

    @computed_field(description="Rol nomi (o'zbekcha)")  # type: ignore[prop-decorator]
    @property
    def role_label(self) -> str:
        return UserRole(self.role).label_uz

    @computed_field(description="Rol izohi")  # type: ignore[prop-decorator]
    @property
    def role_description(self) -> str:
        return UserRole(self.role).description_uz

    @computed_field(description="Jamoa nomi")  # type: ignore[prop-decorator]
    @property
    def team_name(self) -> str | None:
        return self.team.name if self.team is not None else None

    @computed_field(description="Ma'lumot kirita oladimi")  # type: ignore[prop-decorator]
    @property
    def can_write(self) -> bool:
        return UserRole(self.role).can_write


class UserShort(ORMModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None = None
    username: str | None = None
    telegram_id: int | None = None
    role: UserRole
    is_active: bool = True
    team_id: uuid.UUID | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def full_name(self) -> str:
        name = " ".join(p for p in [self.first_name or "", self.last_name or ""] if p).strip()
        return name or (self.username or "Foydalanuvchi")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def role_label(self) -> str:
        return UserRole(self.role).label_uz


class UserCreate(PhoneMixin):
    telegram_id: int | None = Field(default=None, description="Telegram foydalanuvchi ID raqami")
    first_name: Annotated[str, Field(min_length=1, max_length=128)]
    last_name: Annotated[str | None, Field(default=None, max_length=128)] = None
    username: Annotated[str | None, Field(default=None, max_length=64)] = None
    phone: Annotated[str | None, Field(default=None, max_length=32)] = None
    role: UserRole = UserRole.MEASURER
    team_id: uuid.UUID | None = Field(default=None, description="Qaysi jamoaga biriktiriladi")
    is_active: bool = True


class UserUpdate(PhoneMixin):
    first_name: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    last_name: Annotated[str | None, Field(default=None, max_length=128)] = None
    phone: Annotated[str | None, Field(default=None, max_length=32)] = None
    role: UserRole | None = None
    team_id: uuid.UUID | None = Field(default=None, description="Jamoa (bo'shatish uchun null)")
    is_active: bool | None = None


class UserSelfUpdate(PhoneMixin):
    phone: Annotated[str | None, Field(default=None, max_length=32)] = None
    first_name: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    last_name: Annotated[str | None, Field(default=None, max_length=128)] = None


class RoleOption(BaseModel):
    value: UserRole
    label: str
