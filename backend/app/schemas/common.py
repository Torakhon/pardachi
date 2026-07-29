"""Umumiy sxemalar va yordamchi tiplar."""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_RE = re.compile(r"^\+?\d{7,15}$")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PageMeta(BaseModel):
    total: int = Field(description="Jami yozuvlar soni")
    page: int = Field(description="Joriy sahifa")
    size: int = Field(description="Sahifadagi yozuvlar soni")
    pages: int = Field(description="Jami sahifalar soni")


class PaginatedResponse[T](BaseModel):
    items: list[T]
    meta: PageMeta


class MessageResponse(BaseModel):
    message: str = Field(examples=["Muvaffaqiyatli bajarildi."])


class ErrorDetail(BaseModel):
    code: str = Field(examples=["topilmadi"])
    message: str = Field(examples=["So'ralgan ma'lumot topilmadi."])
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


def normalize_phone(value: str) -> str:
    """Telefon raqamini `+998901234567` ko'rinishiga keltiradi."""
    cleaned = re.sub(r"[^\d+]", "", value or "").strip()
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    digits = cleaned.lstrip("+")
    if len(digits) == 9 and digits[0] in "3579":
        # 901234567 -> +998901234567
        cleaned = "+998" + digits
    elif len(digits) == 12 and digits.startswith("998") or not cleaned.startswith("+"):
        cleaned = "+" + digits
    return cleaned


class PhoneMixin(BaseModel):
    @field_validator("customer_phone", "phone", check_fields=False)
    @classmethod
    def _validate_phone(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        normalized = normalize_phone(value)
        if not PHONE_RE.match(normalized):
            raise ValueError("Telefon raqami noto'g'ri. Masalan: +998901234567")
        return normalized


type ShortStr = Annotated[str, Field(min_length=1, max_length=160)]
type OptionalNote = Annotated[str | None, Field(max_length=4000)]
