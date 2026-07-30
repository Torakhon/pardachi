"""Jamoalar biznes logikasi."""

from __future__ import annotations

import uuid

from app.application.permissions import ensure_admin, ensure_can_view_team
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger, log_extra
from app.domain.enums import AuditAction, UserRole
from app.domain.models import Team, User
from app.domain.repositories import UnitOfWork
from app.schemas.team import TeamCreate, TeamMemberAssign, TeamUpdate

logger = get_logger(__name__)


class TeamService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    # ---------------------------------------------------------------- read

    async def list(self, actor: User, *, only_active: bool = False) -> list[Team]:
        """Administrator barcha jamoalarni, boshqalar faqat o'z jamoasini ko'radi."""
        if actor.is_admin:
            return await self._uow.teams.list(only_active=only_active)
        if actor.team_id is None:
            return []
        team = await self._uow.teams.get(actor.team_id)
        return [team] if team is not None else []

    async def get(self, team_id: uuid.UUID, actor: User) -> Team:
        team = await self._require_team(team_id)
        ensure_can_view_team(actor, team)
        return team

    async def members(self, team_id: uuid.UUID, actor: User) -> list[User]:
        team = await self._require_team(team_id)
        ensure_can_view_team(actor, team)
        return await self._uow.teams.members(team_id)

    # --------------------------------------------------------------- write

    async def create(self, payload: TeamCreate, actor: User) -> Team:
        ensure_admin(actor)
        await self._ensure_unique_name(payload.name)

        team = Team(
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            created_by_id=actor.id,
        )
        await self._uow.teams.add(team)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.CREATE,
            entity_type="team",
            entity_id=str(team.id),
            payload={"name": team.name},
        )
        await self._uow.commit()
        logger.info("Jamoa yaratildi", extra=log_extra(team_id=str(team.id), name=team.name))
        # A'zolar bog'lanishi to'lgan holda qaytariladi (yangi obyektda u bo'sh qoladi).
        return await self._require_team(team.id)

    async def update(self, team_id: uuid.UUID, payload: TeamUpdate, actor: User) -> Team:
        ensure_admin(actor)
        team = await self._require_team(team_id)

        data = payload.model_dump(exclude_unset=True)
        new_name = data.pop("name", None)
        if new_name and new_name.lower() != team.name.lower():
            await self._ensure_unique_name(new_name)
            team.name = new_name

        for field, value in data.items():
            setattr(team, field, value)

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="team",
            entity_id=str(team.id),
            payload={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
        )
        await self._uow.commit()
        return await self._require_team(team.id)

    async def delete(self, team_id: uuid.UUID, actor: User) -> None:
        """Jamoada obyekt yoki a'zo bo'lsa o'chirilmaydi — avval ko'chirish kerak."""
        ensure_admin(actor)
        team = await self._require_team(team_id)

        projects_count = await self._uow.projects.count_by_team(team_id)
        if projects_count:
            raise ConflictError(
                f"Bu jamoada {projects_count} ta obyekt bor. O'chirish o'rniga jamoani "
                "faolsizlantiring yoki obyektlarni boshqa jamoaga ko'chiring."
            )

        members = await self._uow.teams.members(team_id)
        if members:
            raise ConflictError(
                f"Bu jamoada {len(members)} ta a'zo bor. Avval ularni boshqa jamoaga o'tkazing."
            )

        await self._uow.teams.delete(team)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.DELETE,
            entity_type="team",
            entity_id=str(team_id),
            payload={"name": team.name},
        )
        await self._uow.commit()

    async def assign_member(self, team_id: uuid.UUID, payload: TeamMemberAssign, actor: User) -> User:
        """Foydalanuvchini jamoaga qo'shadi (Telegram ID yoki mavjud foydalanuvchi ID bo'yicha).

        Telegram ID hali tizimda bo'lmasa, foydalanuvchi oldindan yaratiladi — u
        birinchi marta ilovani ochganda tayyor rol va jamoaga tushadi.
        """
        ensure_admin(actor)
        team = await self._require_team(team_id)

        user = await self._resolve_user(payload)
        if user is None:
            if payload.telegram_id is None:
                raise ValidationError("Telegram ID yoki foydalanuvchi tanlanmagan.")
            user = User(
                telegram_id=payload.telegram_id,
                first_name=payload.first_name or f"Foydalanuvchi {payload.telegram_id}",
                role=payload.role,
                team_id=team.id,
                is_active=True,
            )
            await self._uow.users.add(user)
        else:
            if user.is_admin and payload.role is not UserRole.ADMIN and user.id == actor.id:
                raise ValidationError("O'zingizning admin rolingizni o'zgartira olmaysiz.")
            user.team_id = team.id
            user.role = payload.role
            if payload.first_name:
                user.first_name = payload.first_name

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="team_member",
            entity_id=str(user.id),
            payload={"team_id": str(team.id), "role": user.role.value},
        )
        await self._uow.commit()
        logger.info(
            "Jamoaga a'zo biriktirildi",
            extra=log_extra(team_id=str(team.id), user_id=str(user.id), role=user.role.value),
        )
        return user

    async def remove_member(self, team_id: uuid.UUID, user_id: uuid.UUID, actor: User) -> None:
        ensure_admin(actor)
        await self._require_team(team_id)

        user = await self._uow.users.get(user_id)
        if user is None or user.team_id != team_id:
            raise NotFoundError("Bu foydalanuvchi jamoada topilmadi.")
        if user.id == actor.id:
            raise ValidationError("O'zingizni jamoadan chiqara olmaysiz.")

        user.team_id = None
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPDATE,
            entity_type="team_member",
            entity_id=str(user.id),
            payload={"removed_from": str(team_id)},
        )
        await self._uow.commit()

    # ------------------------------------------------------------ internal

    async def _require_team(self, team_id: uuid.UUID) -> Team:
        team = await self._uow.teams.get(team_id)
        if team is None:
            raise NotFoundError("Jamoa topilmadi.")
        return team

    async def _ensure_unique_name(self, name: str) -> None:
        if await self._uow.teams.get_by_name(name) is not None:
            raise ConflictError(f"«{name}» nomli jamoa allaqachon mavjud.")

    async def _resolve_user(self, payload: TeamMemberAssign) -> User | None:
        if payload.user_id is not None:
            user = await self._uow.users.get(payload.user_id)
            if user is None:
                raise NotFoundError("Foydalanuvchi topilmadi.")
            return user
        if payload.telegram_id is not None:
            return await self._uow.users.get_by_telegram_id(payload.telegram_id)
        return None
