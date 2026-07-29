"""Telegram File API asosidagi saqlagich.

Rasm belgilangan xizmat chatiga yuboriladi, `file_id` bazada saqlanadi.
Telegram `getFile` havolalari vaqtinchalik bo'lgani uchun front-endga
`/api/v1/images/telegram/{file_id}` ko'rinishidagi barqaror havola beriladi —
u so'rov paytida haqiqiy havolaga yo'naltiradi.
"""

from __future__ import annotations

from app.core.config import Settings, settings
from app.core.exceptions import StorageError
from app.infrastructure.storage.base import FileStorage, StoredFile
from app.infrastructure.telegram.client import TelegramClient


class TelegramFileStorage(FileStorage):
    def __init__(self, config: Settings | None = None, client: TelegramClient | None = None) -> None:
        self._config = config or settings
        self._client = client or TelegramClient(self._config)

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
        chat_id = self._config.telegram_storage_chat_id
        if not chat_id:
            raise StorageError("TELEGRAM_STORAGE_CHAT_ID sozlanmagan.")

        result = await self._client.send_photo(chat_id, content, filename, caption)
        photos = result.get("photo") or []
        if not photos:
            raise StorageError("Telegram rasmni qabul qilmadi.")

        largest = max(photos, key=lambda item: int(item.get("file_size") or 0))
        file_id = str(largest["file_id"])

        return StoredFile(
            storage_key=file_id,
            url=f"{self._config.api_prefix}/images/telegram/{file_id}",
            content_type=content_type,
            size_bytes=int(largest.get("file_size") or len(content)),
            width=int(largest.get("width") or 0) or width,
            height=int(largest.get("height") or 0) or height,
            checksum=checksum,
            telegram_file_id=file_id,
        )

    async def delete(self, storage_key: str) -> None:
        """Telegramda yuklangan faylni o'chirish imkoni yo'q — yozuv bazadan olib tashlanadi."""
        return None
