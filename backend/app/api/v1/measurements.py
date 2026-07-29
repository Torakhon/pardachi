"""Alohida o'lchov elementi endpointlari."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path

from app.api.deps import CurrentUser, MeasurementServiceDep
from app.schemas.common import MessageResponse
from app.schemas.measurement import MeasurementItemRead, MeasurementItemUpdate

router = APIRouter(prefix="/measurements", tags=["O'lchovlar"])

ItemId = Annotated[uuid.UUID, Path(description="O'lchov identifikatori")]


@router.get("/{item_id}", response_model=MeasurementItemRead, summary="O'lchov ma'lumoti")
async def get_item(item_id: ItemId, user: CurrentUser, service: MeasurementServiceDep) -> MeasurementItemRead:
    item = await service.get(item_id, user)
    return MeasurementItemRead.model_validate(item)


@router.patch("/{item_id}", response_model=MeasurementItemRead, summary="O'lchovni tahrirlash")
async def update_item(
    item_id: ItemId,
    payload: MeasurementItemUpdate,
    user: CurrentUser,
    service: MeasurementServiceDep,
) -> MeasurementItemRead:
    item = await service.update(item_id, payload, user)
    return MeasurementItemRead.model_validate(item)


@router.delete("/{item_id}", response_model=MessageResponse, summary="O'lchovni o'chirish")
async def delete_item(item_id: ItemId, user: CurrentUser, service: MeasurementServiceDep) -> MessageResponse:
    await service.delete(item_id, user)
    return MessageResponse(message="O'lchov o'chirildi.")
