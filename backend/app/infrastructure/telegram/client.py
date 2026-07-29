"""Telegram Bot API bilan ishlovchi minimal async klient."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)


class TelegramClient:
    def __init__(self, config: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._config = config or settings
        self._client = client
        self._owns_client = client is None

    @property
    def _base_url(self) -> str:
        return f"{self._config.telegram_api_base}/bot{self._config.telegram_bot_token}"

    @property
    def _file_url(self) -> str:
        return f"{self._config.telegram_api_base}/file/bot{self._config.telegram_bot_token}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def _call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.post(f"{self._base_url}/{method}", **kwargs)
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Telegram API xatosi: %s", exc)
            raise StorageError("Telegram serveri bilan bog'lanib bo'lmadi.") from exc

        if not payload.get("ok"):
            description = payload.get("description", "noma'lum xatolik")
            logger.warning("Telegram API rad javobi: %s", description)
            raise StorageError(f"Telegram xatosi: {description}")
        return payload["result"]

    async def send_photo(
        self, chat_id: str, content: bytes, filename: str, caption: str = ""
    ) -> dict[str, Any]:
        return await self._call(
            "sendPhoto",
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"photo": (filename, content, "image/jpeg")},
        )

    async def send_message(self, chat_id: str | int, text: str, **extra: Any) -> dict[str, Any]:
        return await self._call(
            "sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", **extra},
        )

    async def get_file_path(self, file_id: str) -> str:
        result = await self._call("getFile", json={"file_id": file_id})
        return str(result["file_path"])

    async def download_file(self, file_path: str) -> bytes:
        client = await self._get_client()
        try:
            response = await client.get(f"{self._file_url}/{file_path}")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise StorageError("Faylni Telegramdan yuklab bo'lmadi.") from exc
        return response.content

    def public_file_url(self, file_path: str) -> str:
        return f"{self._file_url}/{file_path}"
