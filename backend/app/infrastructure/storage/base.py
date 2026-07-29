"""Fayl saqlash abstraksiyasi."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredFile:
    storage_key: str
    url: str
    content_type: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    checksum: str | None = None
    telegram_file_id: str | None = None


class FileStorage(ABC):
    """Rasm saqlash uchun umumiy interfeys."""

    @abstractmethod
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
    ) -> StoredFile: ...

    @abstractmethod
    async def delete(self, storage_key: str) -> None: ...
