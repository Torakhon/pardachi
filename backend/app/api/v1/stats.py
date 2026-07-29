"""Dashboard, ma'lumotnomalar va salomatlik endpointlari."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import ConfigDep, CurrentUser, SessionDep, StatsServiceDep
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.domain.enums import LocationSource, MeasurementItemType, ProjectStatus, RoomType, UserRole
from app.infrastructure.telegram.client import TelegramClient
from app.schemas.stats import DashboardResponse, HealthResponse

router = APIRouter()


class EnumOption(BaseModel):
    value: str
    label: str


class EnumsResponse(BaseModel):
    room_types: list[EnumOption]
    item_types: list[EnumOption]
    project_statuses: list[EnumOption]
    user_roles: list[EnumOption]
    location_sources: list[EnumOption]
    fabric_types: list[str]
    curtain_models: list[str]


FABRIC_TYPES = [
    "Tyul",
    "Blackout",
    "Baxmal",
    "Jakkard",
    "Zig'ir (len)",
    "Atlas",
    "Organza",
    "Shifon",
    "Rulon parda mato",
]

CURTAIN_MODELS = [
    "Klassik",
    "Rim pardasi",
    "Rulon parda",
    "Jalyuzi",
    "Yapon pardasi",
    "Lambrekenli",
    "Ikki qatlamli",
    "Tyul + portyera",
]


@router.get(
    "/stats/dashboard",
    response_model=DashboardResponse,
    tags=["Statistika"],
    summary="Bosh sahifa statistikasi",
    description="Administrator uchun — barcha obyektlar; o'lchovchi uchun — faqat o'z obyektlari.",
)
async def dashboard(
    user: CurrentUser,
    service: StatsServiceDep,
    recent_limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> DashboardResponse:
    return await service.dashboard(user, recent_limit)


@router.get(
    "/meta/enums",
    response_model=EnumsResponse,
    tags=["Ma'lumotnoma"],
    summary="Ro'yxatlar va ularning o'zbekcha nomlari",
    description="Front-end formalaridagi tanlov ro'yxatlari uchun.",
)
async def enums() -> EnumsResponse:
    return EnumsResponse(
        room_types=[EnumOption(value=item.value, label=item.label_uz) for item in RoomType],
        item_types=[EnumOption(value=item.value, label=item.label_uz) for item in MeasurementItemType],
        project_statuses=[EnumOption(value=item.value, label=item.label_uz) for item in ProjectStatus],
        user_roles=[EnumOption(value=item.value, label=item.label_uz) for item in UserRole],
        location_sources=[EnumOption(value=item.value, label=item.label_uz) for item in LocationSource],
        fabric_types=FABRIC_TYPES,
        curtain_models=CURTAIN_MODELS,
    )


@router.get(
    "/images/telegram/{file_id}",
    tags=["Rasmlar"],
    summary="Telegramda saqlangan rasmga yo'naltirish",
    response_class=RedirectResponse,
)
async def telegram_image(file_id: str, config: ConfigDep) -> Response:
    if config.storage_backend != "telegram":
        raise NotFoundError("Telegram saqlagichi yoqilmagan.")
    client = TelegramClient(config)
    try:
        file_path = await client.get_file_path(file_id)
        return RedirectResponse(url=client.public_file_url(file_path), status_code=307)
    finally:
        await client.aclose()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Xizmat"],
    summary="Servis holati",
)
async def health(session: SessionDep) -> HealthResponse:
    database = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - salomatlik tekshiruvi hech qachon 500 qaytarmaydi
        database = "error"
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        database=database,
    )
