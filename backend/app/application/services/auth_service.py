"""Autentifikatsiya servisi (Telegram initData + JWT)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import Settings, settings
from app.core.exceptions import AuthenticationError, InactiveUserError
from app.core.logging import get_logger, log_extra
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.domain.enums import AuditAction, UserRole
from app.domain.models import User
from app.domain.repositories import UnitOfWork
from app.infrastructure.telegram.init_data import TelegramUser, verify_init_data

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    def __init__(self, uow: UnitOfWork, config: Settings | None = None) -> None:
        self._uow = uow
        self._config = config or settings

    async def login_with_telegram(
        self,
        init_data: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthResult:
        parsed = verify_init_data(
            init_data,
            self._config.telegram_bot_token,
            self._config.telegram_auth_max_age_seconds,
        )
        user = await self._get_or_create(parsed.user)
        return await self._finalize_login(user, ip_address=ip_address, user_agent=user_agent)

    async def dev_login(
        self,
        secret: str,
        telegram_id: int,
        first_name: str,
        role: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthResult:
        if not self._config.allow_dev_login:
            raise AuthenticationError("Dev-login o'chirilgan.")
        if secret != self._config.dev_login_secret:
            raise AuthenticationError("Dev-login maxfiy kaliti noto'g'ri.")

        user = await self._uow.users.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                first_name=first_name or "Sinov",
                username=f"dev{telegram_id}",
                role=UserRole(role),
                is_active=True,
            )
            await self._uow.users.add(user)
        else:
            user.role = UserRole(role)
            user.is_active = True

        return await self._finalize_login(user, ip_address=ip_address, user_agent=user_agent)

    async def refresh(self, refresh_token: str) -> AuthResult:
        payload = decode_token(refresh_token, "refresh", self._config)
        user = await self._uow.users.get(payload.subject)
        if user is None:
            raise AuthenticationError("Foydalanuvchi topilmadi.")
        if not user.is_active:
            raise InactiveUserError()

        return AuthResult(
            user=user,
            access_token=create_access_token(user.id, user.role.value, self._config),
            refresh_token=create_refresh_token(user.id, user.role.value, self._config),
            expires_in=self._config.access_token_expire_minutes * 60,
        )

    async def _get_or_create(self, tg_user: TelegramUser) -> User:
        user = await self._uow.users.get_by_telegram_id(tg_user.id)

        if user is None:
            if not self._config.allow_self_registration and tg_user.id not in self._config.admin_telegram_ids:
                raise AuthenticationError("Siz ro'yxatdan o'tmagansiz. Administratordan ruxsat so'rang.")
            role = await self._resolve_initial_role(tg_user.id)
            user = User(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name or "Foydalanuvchi",
                last_name=tg_user.last_name,
                username=tg_user.username,
                photo_url=tg_user.photo_url,
                language_code=tg_user.language_code or "uz",
                role=role,
                is_active=True,
            )
            await self._uow.users.add(user)
            logger.info(
                "Yangi foydalanuvchi ro'yxatdan o'tdi",
                extra=log_extra(telegram_id=tg_user.id, role=role.value),
            )
        else:
            user.first_name = tg_user.first_name or user.first_name
            user.last_name = tg_user.last_name or user.last_name
            user.username = tg_user.username or user.username
            user.photo_url = tg_user.photo_url or user.photo_url
            if tg_user.id in self._config.admin_telegram_ids and user.role is not UserRole.ADMIN:
                user.role = UserRole.ADMIN

        if not user.is_active:
            raise InactiveUserError()
        return user

    async def _resolve_initial_role(self, telegram_id: int) -> UserRole:
        if telegram_id in self._config.admin_telegram_ids:
            return UserRole.ADMIN
        if self._config.first_user_is_admin and await self._uow.users.count() == 0:
            return UserRole.ADMIN
        return UserRole.MEASURER

    async def _finalize_login(
        self, user: User, *, ip_address: str | None, user_agent: str | None
    ) -> AuthResult:
        user.last_login_at = datetime.now(UTC)
        await self._uow.audit.add(
            actor_id=user.id,
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=str(user.id),
            payload={"telegram_id": user.telegram_id},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._uow.commit()

        return AuthResult(
            user=user,
            access_token=create_access_token(user.id, user.role.value, self._config),
            refresh_token=create_refresh_token(user.id, user.role.value, self._config),
            expires_in=self._config.access_token_expire_minutes * 60,
        )
