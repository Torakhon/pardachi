"""Ilova sozlamalari (environment variables orqali)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Umumiy ---
    app_name: str = "Pardachi API"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # --- Ma'lumotlar bazasi ---
    database_url: str = "postgresql+asyncpg://pardachi:pardachi@localhost:5432/pardachi"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    # --- Xavfsizlik / JWT ---
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    refresh_token_expire_days: int = 30
    # initData imzosining maksimal yoshi (sekund). 0 => tekshirilmaydi.
    telegram_auth_max_age_seconds: int = 86400

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_api_base: str = "https://api.telegram.org"
    # Ushbu telegram ID lar avtomatik ravishda admin bo'ladi
    admin_telegram_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    # Birinchi ro'yxatdan o'tgan foydalanuvchi admin bo'lsinmi
    first_user_is_admin: bool = True
    # Faqat ro'yxatdagi (is_active) foydalanuvchilar kira olsinmi
    allow_self_registration: bool = True
    # Yangi ro'yxatdan o'tgan foydalanuvchining boshlang'ich roli.
    # Sukut bo'yicha "viewer" — administrator uni jamoaga biriktirib, rol beradi.
    default_user_role: Literal["measurer", "viewer"] = "viewer"
    # Birinchi administrator uchun avtomatik yaratiladigan jamoa nomi
    default_team_name: str = "Asosiy jamoa"

    # --- Dev login (Telegramsiz sinov uchun) ---
    allow_dev_login: bool = False
    dev_login_secret: str = "dev-secret"

    # --- Fayl saqlash ---
    storage_backend: Literal["local", "telegram"] = "local"
    media_root: Path = BASE_DIR / "media"
    media_url_prefix: str = "/media"
    max_upload_size_mb: int = 12
    allowed_image_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    image_max_dimension: int = 1600
    image_quality: int = 82
    # storage_backend="telegram" bo'lganda rasm yuboriladigan chat
    telegram_storage_chat_id: str = ""

    # --- CORS ---
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:4173",
            "http://localhost:8080",
        ]
    )
    cors_allow_all: bool = False

    # --- Limitlar ---
    rate_limit_per_minute: int = 240
    max_page_size: int = 100

    @field_validator("admin_telegram_ids", "cors_origins", "allowed_image_types", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """`FOO=1,2,3` ko'rinishidagi env qiymatlarini ro'yxatga aylantiradi."""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return value
            return [part.strip() for part in raw.split(",") if part.strip()]
        return value

    @field_validator("media_root", mode="after")
    @classmethod
    def _ensure_media_root(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def sync_database_url(self) -> str:
        """Alembic uchun sinxron DSN."""
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
