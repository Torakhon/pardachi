"""Jamoa sxemalari."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, computed_field, field_validator, model_validator

from app.domain.enums import UserRole
from app.schemas.common import ORMModel
from app.schemas.user import UserShort


class TeamBase(ORMModel):
    name: Annotated[str, Field(min_length=2, max_length=120, description="Jamoa nomi")]
    description: Annotated[str | None, Field(default=None, max_length=1000)] = None
    is_active: bool = True

    @field_validator("name", "description")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(ORMModel):
    name: Annotated[str | None, Field(default=None, min_length=2, max_length=120)] = None
    description: Annotated[str | None, Field(default=None, max_length=1000)] = None
    is_active: bool | None = None


class TeamRead(TeamBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    members_count: int = 0

    @computed_field(description="Holat nomi")  # type: ignore[prop-decorator]
    @property
    def status_label(self) -> str:
        return "Faol" if self.is_active else "Faol emas"


class TeamWithMembers(TeamRead):
    members: list[UserShort] = Field(default_factory=list)


class TeamShort(ORMModel):
    id: uuid.UUID
    name: str
    is_active: bool = True


class TeamMemberAssign(ORMModel):
    """Jamoaga a'zo qo'shish.

    `telegram_id` yoki `user_id` dan biri ko'rsatilishi shart. Telegram ID hali
    tizimda bo'lmasa, foydalanuvchi oldindan yaratiladi va u ilovaga birinchi
    marta kirganda tayyor rol bilan tushadi.
    """

    telegram_id: Annotated[int | None, Field(default=None, gt=0, description="Telegram ID raqami")] = None
    user_id: uuid.UUID | None = Field(default=None, description="Mavjud foydalanuvchi ID")
    first_name: Annotated[str | None, Field(default=None, max_length=128)] = None
    role: UserRole = Field(default=UserRole.MEASURER, description="Rol: measurer yoki viewer")

    @model_validator(mode="after")
    def _check_identity(self) -> TeamMemberAssign:
        if self.telegram_id is None and self.user_id is None:
            raise ValueError("Telegram ID yoki foydalanuvchini tanlang.")
        return self


class TeamStats(ORMModel):
    team_id: uuid.UUID
    name: str
    projects_count: int
    completed_count: int
