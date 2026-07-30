"""Jamoalar endpointlari."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, TeamServiceDep
from app.schemas.common import MessageResponse
from app.schemas.team import (
    TeamCreate,
    TeamMemberAssign,
    TeamRead,
    TeamUpdate,
    TeamWithMembers,
)
from app.schemas.user import UserShort

router = APIRouter(prefix="/teams", tags=["Jamoalar"])

TeamId = Annotated[uuid.UUID, Path(description="Jamoa identifikatori")]


@router.get(
    "",
    response_model=list[TeamRead],
    summary="Jamoalar ro'yxati",
    description=(
        "Administrator barcha jamoalarni ko'radi. Boshqa foydalanuvchilar faqat "
        "o'zi biriktirilgan jamoani ko'radi."
    ),
)
async def list_teams(
    user: CurrentUser,
    service: TeamServiceDep,
    only_active: Annotated[bool, Query(description="Faqat faol jamoalar")] = False,
) -> list[TeamRead]:
    teams = await service.list(user, only_active=only_active)
    return [TeamRead.model_validate(team) for team in teams]


@router.post(
    "",
    response_model=TeamRead,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi jamoa yaratish (admin)",
)
async def create_team(payload: TeamCreate, user: CurrentUser, service: TeamServiceDep) -> TeamRead:
    team = await service.create(payload, user)
    return TeamRead.model_validate(team)


@router.get(
    "/{team_id}",
    response_model=TeamWithMembers,
    summary="Jamoa ma'lumoti va a'zolari",
)
async def get_team(team_id: TeamId, user: CurrentUser, service: TeamServiceDep) -> TeamWithMembers:
    team = await service.get(team_id, user)
    return TeamWithMembers.model_validate(team)


@router.patch("/{team_id}", response_model=TeamRead, summary="Jamoani tahrirlash (admin)")
async def update_team(
    team_id: TeamId,
    payload: TeamUpdate,
    user: CurrentUser,
    service: TeamServiceDep,
) -> TeamRead:
    team = await service.update(team_id, payload, user)
    return TeamRead.model_validate(team)


@router.delete("/{team_id}", response_model=MessageResponse, summary="Jamoani o'chirish (admin)")
async def delete_team(team_id: TeamId, user: CurrentUser, service: TeamServiceDep) -> MessageResponse:
    await service.delete(team_id, user)
    return MessageResponse(message="Jamoa o'chirildi.")


@router.get(
    "/{team_id}/members",
    response_model=list[UserShort],
    summary="Jamoa a'zolari",
)
async def list_members(team_id: TeamId, user: CurrentUser, service: TeamServiceDep) -> list[UserShort]:
    members = await service.members(team_id, user)
    return [UserShort.model_validate(member) for member in members]


@router.post(
    "/{team_id}/members",
    response_model=UserShort,
    status_code=status.HTTP_201_CREATED,
    summary="Jamoaga a'zo qo'shish yoki rolini o'zgartirish (admin)",
    description=(
        "`telegram_id` bo'yicha qo'shish mumkin — foydalanuvchi hali ilovaga kirmagan bo'lsa ham. "
        "U birinchi marta kirganda tayyor rol va jamoa bilan tushadi."
    ),
)
async def assign_member(
    team_id: TeamId,
    payload: TeamMemberAssign,
    user: CurrentUser,
    service: TeamServiceDep,
) -> UserShort:
    member = await service.assign_member(team_id, payload, user)
    return UserShort.model_validate(member)


@router.delete(
    "/{team_id}/members/{user_id}",
    response_model=MessageResponse,
    summary="A'zoni jamoadan chiqarish (admin)",
)
async def remove_member(
    team_id: TeamId,
    user_id: Annotated[uuid.UUID, Path(description="Foydalanuvchi identifikatori")],
    user: CurrentUser,
    service: TeamServiceDep,
) -> MessageResponse:
    await service.remove_member(team_id, user_id, user)
    return MessageResponse(message="A'zo jamoadan chiqarildi.")
