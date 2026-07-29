"""Telegram WebApp `initData` imzosini tekshirish.

Algoritm rasmiy hujjatga muvofiq:
    secret_key = HMAC_SHA256(key="WebAppData", data=<bot_token>)
    hash       = HMAC_SHA256(key=secret_key, data=<data_check_string>)
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from app.core.exceptions import AuthenticationError


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None
    is_premium: bool = False
    allows_write_to_pm: bool = False


@dataclass(frozen=True, slots=True)
class InitData:
    user: TelegramUser
    auth_date: int
    query_id: str | None = None
    start_param: str | None = None
    chat_type: str | None = None
    raw: dict[str, str] | None = None


def _data_check_string(pairs: dict[str, str]) -> str:
    return "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs) if key != "hash")


def verify_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> InitData:
    """`initData` qatorini tekshiradi va foydalanuvchi ma'lumotini qaytaradi.

    Xatolik bo'lsa `AuthenticationError` ko'tariladi.
    """
    if not bot_token:
        raise AuthenticationError("Server sozlanmagan: bot tokeni ko'rsatilmagan.")
    if not init_data:
        raise AuthenticationError("Telegram ma'lumotlari topilmadi. Ilovani Telegram orqali oching.")

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True, keep_blank_values=True))
    except ValueError as exc:
        raise AuthenticationError("Telegram ma'lumotlari buzilgan.") from exc

    received_hash = pairs.get("hash")
    if not received_hash:
        raise AuthenticationError("Telegram imzosi (hash) topilmadi.")

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, _data_check_string(pairs).encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise AuthenticationError("Telegram imzosi noto'g'ri. Ilovani qaytadan oching.")

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as exc:
        raise AuthenticationError("Telegram vaqt belgisi noto'g'ri.") from exc

    if max_age_seconds > 0 and (time.time() - auth_date) > max_age_seconds:
        raise AuthenticationError("Telegram sessiyasi eskirgan. Ilovani qaytadan oching.")

    user_raw = pairs.get("user")
    if not user_raw:
        raise AuthenticationError("Telegram foydalanuvchi ma'lumoti topilmadi.")

    try:
        user_data = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise AuthenticationError("Telegram foydalanuvchi ma'lumoti buzilgan.") from exc

    if not isinstance(user_data, dict) or "id" not in user_data:
        raise AuthenticationError("Telegram foydalanuvchi ma'lumoti to'liq emas.")

    user = TelegramUser(
        id=int(user_data["id"]),
        first_name=str(user_data.get("first_name") or "").strip(),
        last_name=(str(user_data["last_name"]).strip() if user_data.get("last_name") else None),
        username=(str(user_data["username"]).strip() if user_data.get("username") else None),
        language_code=user_data.get("language_code"),
        photo_url=user_data.get("photo_url"),
        is_premium=bool(user_data.get("is_premium", False)),
        allows_write_to_pm=bool(user_data.get("allows_write_to_pm", False)),
    )

    return InitData(
        user=user,
        auth_date=auth_date,
        query_id=pairs.get("query_id"),
        start_param=pairs.get("start_param"),
        chat_type=pairs.get("chat_type"),
        raw=pairs,
    )
