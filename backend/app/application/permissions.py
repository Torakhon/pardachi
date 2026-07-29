"""Rolga asoslangan ruxsat qoidalari."""

from __future__ import annotations

from app.core.exceptions import PermissionDeniedError
from app.domain.models import Project, User


def is_admin(user: User) -> bool:
    return user.is_admin


def can_view_project(user: User, project: Project) -> bool:
    return user.is_admin or project.created_by_id == user.id


def can_edit_project(user: User, project: Project) -> bool:
    return user.is_admin or project.created_by_id == user.id


def can_delete_project(user: User, project: Project) -> bool:
    """O'lchovchi faqat o'zining yakunlanmagan obyektini o'chira oladi."""
    if user.is_admin:
        return True
    return project.created_by_id == user.id and project.completed_at is None


def ensure_can_view_project(user: User, project: Project) -> None:
    if not can_view_project(user, project):
        raise PermissionDeniedError("Bu obyektni ko'rishga ruxsatingiz yo'q.")


def ensure_can_edit_project(user: User, project: Project) -> None:
    if not can_edit_project(user, project):
        raise PermissionDeniedError("Bu obyektni tahrirlashga ruxsatingiz yo'q.")


def ensure_can_delete_project(user: User, project: Project) -> None:
    if not can_delete_project(user, project):
        raise PermissionDeniedError(
            "Yakunlangan obyektni faqat administrator o'chira oladi."
            if project.completed_at is not None
            else "Bu obyektni o'chirishga ruxsatingiz yo'q."
        )


def ensure_admin(user: User) -> None:
    if not user.is_admin:
        raise PermissionDeniedError("Bu bo'lim faqat administratorlar uchun.")
