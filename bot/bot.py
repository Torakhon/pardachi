"""Pardachi Telegram boti.

Vazifasi — foydalanuvchiga Mini App'ni ochadigan tugmani ko'rsatish.
Long-polling rejimida ishlaydi, faqat `httpx` ga bog'liq.

Ishga tushirish:
    TELEGRAM_BOT_TOKEN=... WEBAPP_URL=https://example.com python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

import httpx

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pardachi.bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
WEBAPP_URL = os.environ.get("WEBAPP_URL", "").strip()
API_BASE = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")

WELCOME = (
    "<b>Pardachi</b> — parda o‘lchov tizimi.\n\n"
    "Bu ilova orqali siz:\n"
    "• yangi obyekt yaratasiz;\n"
    "• xonalarni qo‘shasiz va rasmga olasiz;\n"
    "• oyna va eshiklarning o‘lchamlarini kiritasiz;\n"
    "• barcha ma’lumotlarni bir joyda saqlaysiz.\n\n"
    "Boshlash uchun pastdagi tugmani bosing 👇"
)

HELP = (
    "<b>Yordam</b>\n\n"
    "/start — ilovani ochish\n"
    "/id — Telegram ID raqamingiz\n"
    "/help — ushbu yordam\n\n"
    "Savol va takliflar bo‘yicha administratorga murojaat qiling."
)


def keyboard() -> dict[str, Any]:
    return {
        "keyboard": [[{"text": "📏 Ilovani ochish", "web_app": {"url": WEBAPP_URL}}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


class Bot:
    def __init__(self, token: str) -> None:
        self._base = f"{API_BASE}/bot{token}"
        self._offset = 0
        self._running = True

    async def call(self, client: httpx.AsyncClient, method: str, **payload: Any) -> Any:
        response = await client.post(f"{self._base}/{method}", json=payload, timeout=65)
        data = response.json()
        if not data.get("ok"):
            logger.warning("Telegram xatosi (%s): %s", method, data.get("description"))
            return None
        return data["result"]

    async def setup(self, client: httpx.AsyncClient) -> None:
        await self.call(
            client,
            "setMyCommands",
            commands=[
                {"command": "start", "description": "Ilovani ochish"},
                {"command": "id", "description": "Telegram ID raqamim"},
                {"command": "help", "description": "Yordam"},
            ],
        )
        if WEBAPP_URL:
            await self.call(
                client,
                "setChatMenuButton",
                menu_button={"type": "web_app", "text": "Pardachi", "web_app": {"url": WEBAPP_URL}},
            )
        me = await self.call(client, "getMe")
        if me:
            logger.info("Bot ishga tushdi: @%s", me.get("username"))

    async def handle(self, client: httpx.AsyncClient, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        first_name = message.get("from", {}).get("first_name", "")

        if text.startswith("/start"):
            await self.call(
                client,
                "sendMessage",
                chat_id=chat_id,
                text=f"Assalomu alaykum, {first_name}!\n\n{WELCOME}",
                parse_mode="HTML",
                reply_markup=keyboard(),
            )
        elif text.startswith("/help"):
            await self.call(client, "sendMessage", chat_id=chat_id, text=HELP, parse_mode="HTML")
        elif text.startswith("/id"):
            user_id = message.get("from", {}).get("id")
            await self.call(
                client,
                "sendMessage",
                chat_id=chat_id,
                text=(
                    f"Sizning Telegram ID raqamingiz: <code>{user_id}</code>\n\n"
                    "Administrator bo'lish uchun bu raqamni serverdagi <code>.env</code> faylida "
                    "<code>ADMIN_TELEGRAM_IDS</code> ga yozing va backendni qayta ishga tushiring."
                ),
                parse_mode="HTML",
            )
        elif "web_app_data" in message:
            logger.info("WebApp ma'lumoti keldi: %s", message["web_app_data"].get("data"))
        else:
            await self.call(
                client,
                "sendMessage",
                chat_id=chat_id,
                text="Ilovani ochish uchun pastdagi tugmani bosing 👇",
                reply_markup=keyboard(),
            )

    async def poll(self) -> None:
        async with httpx.AsyncClient() as client:
            await self.setup(client)
            while self._running:
                try:
                    updates = await self.call(
                        client, "getUpdates", offset=self._offset, timeout=30, allowed_updates=["message"]
                    )
                except httpx.HTTPError as exc:
                    logger.warning("Tarmoq xatosi: %s", exc)
                    await asyncio.sleep(3)
                    continue

                for update in updates or []:
                    self._offset = update["update_id"] + 1
                    try:
                        await self.handle(client, update)
                    except Exception:  # noqa: BLE001 - bitta xato botni to'xtatmasin
                        logger.exception("Update qayta ishlashda xatolik")

    def stop(self) -> None:
        self._running = False


async def main() -> None:
    if not BOT_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN o'rnatilmagan.")
    if not WEBAPP_URL:
        sys.exit("WEBAPP_URL o'rnatilmagan (Mini App manzili).")

    bot = Bot(BOT_TOKEN)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with_suppress(loop, sig, bot.stop)

    await bot.poll()
    logger.info("Bot to'xtatildi")


def with_suppress(loop: asyncio.AbstractEventLoop, sig: signal.Signals, handler: Any) -> None:
    try:
        loop.add_signal_handler(sig, handler)
    except NotImplementedError:  # Windows
        signal.signal(sig, lambda *_: handler())


if __name__ == "__main__":
    asyncio.run(main())
