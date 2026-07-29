"""Autentifikatsiya endpointlari."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import AuthServiceDep, CurrentUser, UserServiceDep, client_ip
from app.application.services.auth_service import AuthResult
from app.schemas.auth import (
    DevLoginRequest,
    RefreshRequest,
    TelegramLoginRequest,
    TokenResponse,
)
from app.schemas.user import UserRead, UserSelfUpdate

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya"])


def _to_response(result: AuthResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_in=result.expires_in,
        user=UserRead.model_validate(result.user),
    )


@router.post(
    "/telegram",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Telegram orqali kirish",
    description=(
        "Telegram Mini App `initData` qatorini tekshiradi va JWT tokenlar qaytaradi. "
        "Foydalanuvchi birinchi marta kirsa, avtomatik ro'yxatdan o'tkaziladi."
    ),
)
async def login_telegram(
    payload: TelegramLoginRequest,
    request: Request,
    service: AuthServiceDep,
) -> TokenResponse:
    result = await service.login_with_telegram(
        payload.init_data,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _to_response(result)


@router.post(
    "/dev-login",
    response_model=TokenResponse,
    summary="Sinov uchun kirish (faqat development)",
    description="`ALLOW_DEV_LOGIN=true` bo'lgandagina ishlaydi. Telegramsiz test qilish uchun.",
)
async def dev_login(
    payload: DevLoginRequest,
    request: Request,
    service: AuthServiceDep,
) -> TokenResponse:
    result = await service.dev_login(
        payload.secret,
        payload.telegram_id,
        payload.first_name,
        payload.role,
        ip_address=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _to_response(result)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Tokenni yangilash",
    description="Refresh token orqali yangi access token oladi.",
)
async def refresh_token(payload: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    result = await service.refresh(payload.refresh_token)
    return _to_response(result)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Joriy foydalanuvchi ma'lumoti",
)
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="O'z profilini tahrirlash",
)
async def update_me(
    payload: UserSelfUpdate,
    user: CurrentUser,
    service: UserServiceDep,
) -> UserRead:
    updated = await service.update_self(payload, user)
    return UserRead.model_validate(updated)
