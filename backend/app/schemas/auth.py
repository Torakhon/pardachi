"""Autentifikatsiya sxemalari."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class TelegramLoginRequest(BaseModel):
    init_data: str = Field(
        min_length=1,
        max_length=8192,
        description="Telegram WebApp `window.Telegram.WebApp.initData` qiymati",
    )


class DevLoginRequest(BaseModel):
    """Faqat ALLOW_DEV_LOGIN=true bo'lganda ishlaydi (Telegramsiz sinov uchun)."""

    secret: str = Field(min_length=1, description="DEV_LOGIN_SECRET qiymati")
    telegram_id: int = Field(default=1000000001, description="Soxta Telegram ID")
    first_name: str = Field(default="Sinov", max_length=128)
    role: str = Field(default="measurer", pattern="^(admin|measurer)$")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token amal qilish muddati (sekund)")
    user: UserRead
