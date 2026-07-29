"""Telegram initData imzosini tekshirish testlari."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.exceptions import AuthenticationError
from app.infrastructure.telegram.init_data import verify_init_data

BOT_TOKEN = "123456:TEST-BOT-TOKEN"


def build_init_data(bot_token: str = BOT_TOKEN, *, auth_date: int | None = None, user_id: int = 42) -> str:
    user = {"id": user_id, "first_name": "Rustam", "username": "rustam", "language_code": "uz"}
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAF_test",
        "user": json.dumps(user, separators=(",", ":")),
    }
    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_valid_init_data_is_accepted() -> None:
    parsed = verify_init_data(build_init_data(), BOT_TOKEN)
    assert parsed.user.id == 42
    assert parsed.user.first_name == "Rustam"
    assert parsed.user.username == "rustam"


def test_tampered_payload_is_rejected() -> None:
    init_data = build_init_data().replace("Rustam", "Hacker")
    with pytest.raises(AuthenticationError) as exc:
        verify_init_data(init_data, BOT_TOKEN)
    assert "imzosi" in str(exc.value)


def test_wrong_bot_token_is_rejected() -> None:
    with pytest.raises(AuthenticationError):
        verify_init_data(build_init_data(), "999999:OTHER-TOKEN")


def test_expired_init_data_is_rejected() -> None:
    old = int(time.time()) - 10_000
    with pytest.raises(AuthenticationError) as exc:
        verify_init_data(build_init_data(auth_date=old), BOT_TOKEN, max_age_seconds=3600)
    assert "eskirgan" in str(exc.value)


def test_expiry_check_can_be_disabled() -> None:
    old = int(time.time()) - 10_000
    parsed = verify_init_data(build_init_data(auth_date=old), BOT_TOKEN, max_age_seconds=0)
    assert parsed.auth_date == old


def test_missing_hash_is_rejected() -> None:
    with pytest.raises(AuthenticationError):
        verify_init_data("auth_date=1&user=%7B%22id%22%3A1%7D", BOT_TOKEN)


def test_empty_init_data_is_rejected() -> None:
    with pytest.raises(AuthenticationError):
        verify_init_data("", BOT_TOKEN)
