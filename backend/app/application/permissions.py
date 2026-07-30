"""Rol va jamoaga asoslangan ruxsat qoidalari.

Qoidalar qisqacha:

| Rol           | Ko'rish                | Yaratish/Tahrirlash           | O'chirish                  |
|---------------|------------------------|-------------------------------|----------------------------|
| Administrator | barcha jamoalar        | barcha obyektlar              | barcha obyektlar           |
| O'lchovchi    | o'z jamoasi obyektlari | o'z jamoasida, o'z obyektlari | o'zining yakunlanmaganlari |
| Ko'ruvchi     | o'z jamoasi obyektlari | — (faqat o'qish)              | —                          |

Jamoaga biriktirilmagan foydalanuvchi hech qanday obyektni ko'ra olmaydi.
"""

from __future__ import annotations

from app.core.exceptions import PermissionDeniedError, ValidationError
from app.domain.models import Project, Team, User

NO_TEAM_MESSAGE = "Siz hech qanday jamoaga biriktirilmagansiz. Administrator sizni jamoaga qo'shishi kerak."
READ_ONLY_MESSAGE = "Sizning rolingiz «Ko'ruvchi» — ma'lumotlarni faqat ko'ra olasiz."


def is_admin(user: User) -> bool:
    return user.is_admin


def same_team(user: User, project: Project) -> bool:
    return user.team_id is not None and project.team_id == user.team_id


# ------------------------------------------------------------------ ko'rish


def can_view_project(user: User, project: Project) -> bool:
    return user.is_admin or same_team(user, project)


def ensure_can_view_project(user: User, project: Project) -> None:
    if not can_view_project(user, project):
        raise PermissionDeniedError("Bu obyekt boshqa jamoaga tegishli — ko'rishga ruxsatingiz yo'q.")


# -------------------------------------------------------------- tahrirlash


def can_edit_project(user: User, project: Project) -> bool:
    if user.is_admin:
        return True
    if not user.can_write or not same_team(user, project):
        return False
    # O'lchovchi faqat o'zi yaratgan obyektni tahrirlaydi.
    return project.created_by_id == user.id


def ensure_can_edit_project(user: User, project: Project) -> None:
    if can_edit_project(user, project):
        return
    if not user.can_write:
        raise PermissionDeniedError(READ_ONLY_MESSAGE)
    if not same_team(user, project):
        raise PermissionDeniedError("Bu obyekt boshqa jamoaga tegishli.")
    raise PermissionDeniedError(
        "Bu obyektni boshqa o'lchovchi yaratgan. Faqat administrator yoki muallif tahrirlay oladi."
    )


# ---------------------------------------------------------------- o'chirish


def can_delete_project(user: User, project: Project) -> bool:
    if user.is_admin:
        return True
    if not user.can_write or not same_team(user, project):
        return False
    return project.created_by_id == user.id and project.completed_at is None


def ensure_can_delete_project(user: User, project: Project) -> None:
    if can_delete_project(user, project):
        return
    if not user.can_write:
        raise PermissionDeniedError(READ_ONLY_MESSAGE)
    if project.completed_at is not None:
        raise PermissionDeniedError("Yakunlangan obyektni faqat administrator o'chira oladi.")
    raise PermissionDeniedError("Bu obyektni o'chirishga ruxsatingiz yo'q.")


# -------------------------------------------------------------- yaratish


def ensure_can_create_project(user: User) -> None:
    """Yangi obyekt yaratish uchun: yozish huquqi + jamoa bo'lishi shart."""
    if user.is_admin:
        return
    if not user.can_write:
        raise PermissionDeniedError(READ_ONLY_MESSAGE)
    if user.team_id is None:
        raise ValidationError(NO_TEAM_MESSAGE)


def ensure_write_role(user: User) -> None:
    if not user.can_write:
        raise PermissionDeniedError(READ_ONLY_MESSAGE)


# ---------------------------------------------------------------- jamoalar


def can_view_team(user: User, team: Team) -> bool:
    return user.is_admin or user.team_id == team.id


def ensure_can_view_team(user: User, team: Team) -> None:
    if not can_view_team(user, team):
        raise PermissionDeniedError("Bu jamoa ma'lumotlarini ko'rishga ruxsatingiz yo'q.")


def ensure_admin(user: User) -> None:
    if not user.is_admin:
        raise PermissionDeniedError("Bu bo'lim faqat administratorlar uchun.")
