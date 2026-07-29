"""JWT tokenlar bilan ishlash."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt

from app.core.config import Settings, settings
from app.core.exceptions import AuthenticationError

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True, slots=True)
class TokenPayload:
    subject: uuid.UUID
    role: str
    token_type: TokenType
    expires_at: datetime
    jti: str


def _create_token(
    subject: uuid.UUID,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
    config: Settings | None = None,
) -> str:
    config = config or settings
    now = datetime.now(UTC)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, config.secret_key, algorithm=config.jwt_algorithm)


def create_access_token(subject: uuid.UUID, role: str, config: Settings | None = None) -> str:
    config = config or settings
    return _create_token(
        subject, role, "access", timedelta(minutes=config.access_token_expire_minutes), config
    )


def create_refresh_token(subject: uuid.UUID, role: str, config: Settings | None = None) -> str:
    config = config or settings
    return _create_token(subject, role, "refresh", timedelta(days=config.refresh_token_expire_days), config)


def decode_token(
    token: str,
    expected_type: TokenType = "access",
    config: Settings | None = None,
) -> TokenPayload:
    config = config or settings
    try:
        data = jwt.decode(token, config.secret_key, algorithms=[config.jwt_algorithm])
    except JWTError as exc:  # noqa: BLE001 - barcha jose xatolari bir xil qaytadi
        raise AuthenticationError("Token yaroqsiz yoki muddati tugagan.") from exc

    if data.get("type") != expected_type:
        raise AuthenticationError("Token turi noto'g'ri.")

    subject_raw = data.get("sub")
    if not subject_raw:
        raise AuthenticationError("Tokenda foydalanuvchi ma'lumoti yo'q.")

    try:
        subject = uuid.UUID(str(subject_raw))
    except ValueError as exc:
        raise AuthenticationError("Tokendagi foydalanuvchi identifikatori noto'g'ri.") from exc

    return TokenPayload(
        subject=subject,
        role=str(data.get("role", "")),
        token_type=expected_type,
        expires_at=datetime.fromtimestamp(int(data["exp"]), tz=UTC),
        jti=str(data.get("jti", "")),
    )
