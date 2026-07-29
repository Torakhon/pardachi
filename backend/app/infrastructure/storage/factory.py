"""Sozlamaga qarab kerakli saqlagichni tanlaydi."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, settings
from app.infrastructure.storage.base import FileStorage
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.infrastructure.storage.telegram_storage import TelegramFileStorage


def build_storage(config: Settings | None = None) -> FileStorage:
    config = config or settings
    if config.storage_backend == "telegram":
        return TelegramFileStorage(config)
    return LocalFileStorage(config)


@lru_cache
def get_storage() -> FileStorage:
    return build_storage()
