"""Foydalanuvchi sxemalari."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, computed_field

from app.domain.enums import UserRole
from app.schemas.common import ORMModel, PhoneMixin


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


class UserShort(ORMModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None = None
    username: str | None = None
    role: UserRole

    @computed_field  # type: ignore[prop-decorator]
    @property
    def full_name(self) -> str:
        name = " ".join(p for p in [self.first_name or "", self.last_name or ""] if p).strip()
        return name or (self.username or "Foydalanuvchi")


class UserCreate(PhoneMixin):
    telegram_id: int | None = Field(default=None, description="Telegram foydalanuvchi ID raqami")
    first_name: Annotated[str, Field(min_length=1, max_length=128)]
    last_name: Annotated[str | None, Field(default=None, max_length=128)] = None
    username: Annotated[str | None, Field(default=None, max_length=64)] = None
    phone: Annotated[str | None, Field(default=None, max_length=32)] = None
    role: UserRole = UserRole.MEASURER
    is_active: bool = True


class UserUpdate(PhoneMixin):
    first_name: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    last_name: Annotated[str | None, Field(default=None, max_length=128)] = None
    phone: Annotated[str | None, Field(default=None, max_length=32)] = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserSelfUpdate(PhoneMixin):
    phone: Annotated[str | None, Field(default=None, max_length=32)] = None
    first_name: Annotated[str | None, Field(default=None, min_length=1, max_length=128)] = None
    last_name: Annotated[str | None, Field(default=None, max_length=128)] = None


class RoleOption(BaseModel):
    value: UserRole
    label: str
