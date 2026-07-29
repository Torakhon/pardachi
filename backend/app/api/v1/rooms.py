"""Xona, xona rasmi va xonadagi o'lchovlar endpointlari."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Path, Query, UploadFile, status
from pydantic import BaseModel

from app.api.deps import (
    CurrentUser,
    ImageServiceDep,
    MeasurementServiceDep,
    RoomServiceDep,
)
from app.core.exceptions import ValidationError
from app.domain.enums import MeasurementItemType
from app.schemas.common import MessageResponse
from app.schemas.measurement import (
    MeasurementItemCreate,
    MeasurementItemRead,
    MeasurementItemReorder,
)
from app.schemas.room import RoomImageRead, RoomRead, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["Xonalar"])

RoomId = Annotated[uuid.UUID, Path(description="Xona identifikatori")]


class SuggestedName(BaseModel):
    name: str


@router.get("/{room_id}", response_model=RoomRead, summary="Xona ma'lumoti")
async def get_room(room_id: RoomId, user: CurrentUser, service: RoomServiceDep) -> RoomRead:
    room = await service.get(room_id, user)
    return RoomRead.model_validate(room)


@router.patch("/{room_id}", response_model=RoomRead, summary="Xonani tahrirlash")
async def update_room(
    room_id: RoomId,
    payload: RoomUpdate,
    user: CurrentUser,
    service: RoomServiceDep,
) -> RoomRead:
    room = await service.update(room_id, payload, user)
    return RoomRead.model_validate(room)


@router.delete("/{room_id}", response_model=MessageResponse, summary="Xonani o'chirish")
async def delete_room(room_id: RoomId, user: CurrentUser, service: RoomServiceDep) -> MessageResponse:
    await service.delete(room_id, user)
    return MessageResponse(message="Xona o'chirildi.")


# ----------------------------------------------------------------- rasm


@router.post(
    "/{room_id}/image",
    response_model=RoomImageRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Rasmlar"],
    summary="Xona rasmini yuklash yoki almashtirish",
    description=(
        "Har bir xonada aynan bitta rasm bo'ladi. Yangi rasm yuklansa, eskisi o'chiriladi. "
        "Rasm serverda ham siqiladi (maksimal tomon 1600px, JPEG)."
    ),
)
async def upload_room_image(
    room_id: RoomId,
    user: CurrentUser,
    service: ImageServiceDep,
    file: Annotated[UploadFile, File(description="Rasm fayli (JPG/PNG/WEBP)")],
) -> RoomImageRead:
    content = await file.read()
    if not content:
        raise ValidationError("Rasm fayli bo'sh.")
    image = await service.upload(
        room_id,
        content=content,
        content_type=file.content_type or "image/jpeg",
        actor=user,
    )
    return RoomImageRead.model_validate(image)


@router.get(
    "/{room_id}/image",
    response_model=RoomImageRead,
    tags=["Rasmlar"],
    summary="Xona rasmi ma'lumoti",
)
async def get_room_image(room_id: RoomId, user: CurrentUser, service: ImageServiceDep) -> RoomImageRead:
    image = await service.get_for_room(room_id, user)
    return RoomImageRead.model_validate(image)


@router.delete(
    "/{room_id}/image",
    response_model=MessageResponse,
    tags=["Rasmlar"],
    summary="Xona rasmini o'chirish",
)
async def delete_room_image(room_id: RoomId, user: CurrentUser, service: ImageServiceDep) -> MessageResponse:
    await service.delete(room_id, user)
    return MessageResponse(message="Rasm o'chirildi.")


# -------------------------------------------------------------- o'lchovlar


@router.get(
    "/{room_id}/items",
    response_model=list[MeasurementItemRead],
    tags=["O'lchovlar"],
    summary="Xonadagi o'lchovlar",
)
async def list_items(
    room_id: RoomId, user: CurrentUser, service: MeasurementServiceDep
) -> list[MeasurementItemRead]:
    items = await service.list_by_room(room_id, user)
    return [MeasurementItemRead.model_validate(item) for item in items]


@router.post(
    "/{room_id}/items",
    response_model=MeasurementItemRead,
    status_code=status.HTTP_201_CREATED,
    tags=["O'lchovlar"],
    summary="O'lchov qo'shish (oyna yoki eshik)",
)
async def create_item(
    room_id: RoomId,
    payload: MeasurementItemCreate,
    user: CurrentUser,
    service: MeasurementServiceDep,
) -> MeasurementItemRead:
    item = await service.create(room_id, payload, user)
    return MeasurementItemRead.model_validate(item)


@router.get(
    "/{room_id}/items/suggest-name",
    response_model=SuggestedName,
    tags=["O'lchovlar"],
    summary="Yangi o'lchov uchun nom taklifi",
)
async def suggest_item_name(
    room_id: RoomId,
    user: CurrentUser,
    service: MeasurementServiceDep,
    item_type: Annotated[MeasurementItemType, Query(description="Tur: window | door")],
) -> SuggestedName:
    await service.list_by_room(room_id, user)  # ruxsatni tekshiradi
    return SuggestedName(name=await service.suggest_name(room_id, item_type))


@router.post(
    "/{room_id}/items/reorder",
    response_model=list[MeasurementItemRead],
    tags=["O'lchovlar"],
    summary="O'lchovlar tartibini o'zgartirish",
)
async def reorder_items(
    room_id: RoomId,
    payload: MeasurementItemReorder,
    user: CurrentUser,
    service: MeasurementServiceDep,
) -> list[MeasurementItemRead]:
    items = await service.reorder(room_id, payload.item_ids, user)
    return [MeasurementItemRead.model_validate(item) for item in items]
