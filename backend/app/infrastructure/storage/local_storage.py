"""Lokal disk saqlagichi (development va kichik o'rnatishlar uchun)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings, settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger
from app.infrastructure.storage.base import FileStorage, StoredFile

logger = get_logger(__name__)


class LocalFileStorage(FileStorage):
    def __init__(self, config: Settings | None = None) -> None:
        self._config = config or settings
        self._root: Path = self._config.media_root
        self._root.mkdir(parents=True, exist_ok=True)

    def _absolute(self, storage_key: str) -> Path:
        path = (self._root / storage_key).resolve()
        root = self._root.resolve()
        if not str(path).startswith(str(root)):
            raise StorageError("Fayl yo'li noto'g'ri.")
        return path

    async def save(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str,
        width: int | None = None,
        height: int | None = None,
        checksum: str | None = None,
        caption: str = "",
    ) -> StoredFile:
        today = datetime.now(UTC)
        storage_key = f"rooms/{today:%Y/%m}/{filename}"
        target = self._absolute(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)

        def _write() -> None:
            temp = target.with_suffix(target.suffix + ".tmp")
            temp.write_bytes(content)
            temp.replace(target)

        try:
            await asyncio.to_thread(_write)
        except OSError as exc:
            logger.exception("Faylni saqlab bo'lmadi: %s", storage_key)
            raise StorageError("Rasmni serverga saqlab bo'lmadi.") from exc

        return StoredFile(
            storage_key=storage_key,
            url=f"{self._config.media_url_prefix}/{storage_key}",
            content_type=content_type,
            size_bytes=len(content),
            width=width,
            height=height,
            checksum=checksum,
        )

    async def delete(self, storage_key: str) -> None:
        target = self._absolute(storage_key)

        def _remove() -> None:
            target.unlink(missing_ok=True)

        try:
            await asyncio.to_thread(_remove)
        except OSError as exc:
            logger.warning("Faylni o'chirib bo'lmadi (%s): %s", storage_key, exc)
