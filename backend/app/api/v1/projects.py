"""Obyekt (loyiha) endpointlari."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    CurrentUser,
    MeasurementServiceDep,
    PaginationDep,
    ProjectServiceDep,
    RoomServiceDep,
)
from app.domain.enums import ProjectStatus
from app.domain.repositories import Page
from app.schemas.common import MessageResponse, PageMeta, PaginatedResponse
from app.schemas.measurement import MeasurementItemRead
from app.schemas.project import (
    LocationCreate,
    ProjectCreate,
    ProjectRead,
    ProjectStatusUpdate,
    ProjectSummary,
    ProjectUpdate,
)
from app.schemas.room import RoomCreate, RoomRead, RoomReorder

router = APIRouter(prefix="/projects", tags=["Obyektlar"])

ProjectId = Annotated[uuid.UUID, Path(description="Obyekt identifikatori")]


class OrderNumberResponse(BaseModel):
    order_number: str = Field(examples=["OB-20260729-001"])


def _paginate(page: Page) -> PaginatedResponse[ProjectSummary]:
    return PaginatedResponse[ProjectSummary](
        items=[ProjectSummary.model_validate(item) for item in page.items],
        meta=PageMeta(total=page.total, page=page.page, size=page.size, pages=page.pages),
    )


@router.get(
    "",
    response_model=PaginatedResponse[ProjectSummary],
    summary="Obyektlar ro'yxati",
    description=(
        "Qidiruv (obyekt nomi, mijoz ismi, buyurtma raqami, telefon), holat, o'lchovchi va sana "
        "bo'yicha filtrlash. O'lchovchi faqat o'z obyektlarini ko'radi."
    ),
)
async def list_projects(
    user: CurrentUser,
    service: ProjectServiceDep,
    pagination: PaginationDep,
    search: Annotated[str | None, Query(max_length=160, description="Qidiruv matni")] = None,
    project_status: Annotated[ProjectStatus | None, Query(alias="status", description="Holat")] = None,
    measurer_id: Annotated[uuid.UUID | None, Query(description="O'lchovchi ID bo'yicha filtr")] = None,
    team_id: Annotated[uuid.UUID | None, Query(description="Jamoa ID (faqat admin)")] = None,
    date_from: Annotated[date | None, Query(description="Sanadan")] = None,
    date_to: Annotated[date | None, Query(description="Sanagacha")] = None,
    order_by: Annotated[str, Query(description="Saralash: -created_at, name, status ...")] = "-created_at",
) -> PaginatedResponse[ProjectSummary]:
    page = await service.list(
        user,
        search=search,
        status=project_status,
        measurer_id=measurer_id,
        team_id=team_id,
        date_from=date_from,
        date_to=date_to,
        order_by=order_by,
        page=pagination.page,
        size=pagination.size,
    )
    return _paginate(page)


@router.get(
    "/recent",
    response_model=list[ProjectSummary],
    summary="Oxirgi obyektlar",
)
async def recent_projects(
    user: CurrentUser,
    service: ProjectServiceDep,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[ProjectSummary]:
    projects = await service.recent(user, limit)
    return [ProjectSummary.model_validate(project) for project in projects]


@router.get(
    "/next-order-number",
    response_model=OrderNumberResponse,
    summary="Keyingi bo'sh buyurtma raqami",
)
async def next_order_number(user: CurrentUser, service: ProjectServiceDep) -> OrderNumberResponse:
    return OrderNumberResponse(order_number=await service.next_order_number())


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi obyekt yaratish",
    description=(
        "Oflayn rejimda yaratilgan yozuvlarni sinxronlash uchun `id` maydonini yuborish mumkin — "
        "bir xil `id` bilan takroriy so'rov yangi obyekt yaratmaydi."
    ),
)
async def create_project(
    payload: ProjectCreate,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.create(payload, user)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead, summary="Obyekt ma'lumoti")
async def get_project(
    project_id: ProjectId,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.get(project_id, user)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead, summary="Obyektni tahrirlash")
async def update_project(
    project_id: ProjectId,
    payload: ProjectUpdate,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.update(project_id, payload, user)
    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}/status",
    response_model=ProjectRead,
    summary="Obyekt holatini o'zgartirish",
    description="Yakunlash uchun har bir xonada rasm va kamida bitta o'lchov bo'lishi shart.",
)
async def change_status(
    project_id: ProjectId,
    payload: ProjectStatusUpdate,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.change_status(project_id, payload.status, user)
    return ProjectRead.model_validate(project)


@router.post(
    "/{project_id}/location",
    response_model=ProjectRead,
    summary="Obyekt lokatsiyasini saqlash",
)
async def set_location(
    project_id: ProjectId,
    payload: LocationCreate,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.set_location(project_id, payload, user)
    return ProjectRead.model_validate(project)


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    summary="Obyektni o'chirish",
    description="Odatiy holda arxivga olinadi (soft delete). `hard=true` — faqat administrator uchun.",
)
async def delete_project(
    project_id: ProjectId,
    user: CurrentUser,
    service: ProjectServiceDep,
    hard: Annotated[bool, Query(description="Butunlay o'chirish (admin)")] = False,
) -> MessageResponse:
    await service.delete(project_id, user, hard=hard)
    return MessageResponse(message="Obyekt o'chirildi.")


@router.post(
    "/{project_id}/restore",
    response_model=ProjectRead,
    summary="O'chirilgan obyektni tiklash (admin)",
)
async def restore_project(
    project_id: ProjectId,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.restore(project_id, user)
    return ProjectRead.model_validate(project)


# --------------------------------------------------------------- xonalar


@router.get(
    "/{project_id}/rooms",
    response_model=list[RoomRead],
    tags=["Xonalar"],
    summary="Obyekt xonalari",
)
async def list_rooms(
    project_id: ProjectId,
    user: CurrentUser,
    service: RoomServiceDep,
) -> list[RoomRead]:
    rooms = await service.list_by_project(project_id, user)
    return [RoomRead.model_validate(room) for room in rooms]


@router.post(
    "/{project_id}/rooms",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Xonalar"],
    summary="Xona qo'shish",
)
async def create_room(
    project_id: ProjectId,
    payload: RoomCreate,
    user: CurrentUser,
    service: RoomServiceDep,
) -> RoomRead:
    room = await service.create(project_id, payload, user)
    return RoomRead.model_validate(room)


@router.post(
    "/{project_id}/rooms/reorder",
    response_model=list[RoomRead],
    tags=["Xonalar"],
    summary="Xonalar tartibini o'zgartirish",
)
async def reorder_rooms(
    project_id: ProjectId,
    payload: RoomReorder,
    user: CurrentUser,
    service: RoomServiceDep,
) -> list[RoomRead]:
    rooms = await service.reorder(project_id, payload.room_ids, user)
    return [RoomRead.model_validate(room) for room in rooms]


@router.get(
    "/{project_id}/measurements",
    response_model=list[MeasurementItemRead],
    tags=["O'lchovlar"],
    summary="Obyektdagi barcha o'lchovlar",
    description="Tikuv bo'limi uchun yagona ro'yxat (xonalar tartibida).",
)
async def project_measurements(
    project_id: ProjectId,
    user: CurrentUser,
    service: MeasurementServiceDep,
) -> list[MeasurementItemRead]:
    items = await service.list_by_project(project_id, user)
    return [MeasurementItemRead.model_validate(item) for item in items]
