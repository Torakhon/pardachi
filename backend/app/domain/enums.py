"""Domen enumlari va ularning o'zbekcha nomlari."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MEASURER = "measurer"

    @property
    def label_uz(self) -> str:
        return {"admin": "Administrator", "measurer": "O'lchovchi"}[self.value]


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @property
    def label_uz(self) -> str:
        return {
            "draft": "Yangi",
            "in_progress": "Jarayonda",
            "completed": "Yakunlangan",
            "cancelled": "Bekor qilingan",
        }[self.value]


class MeasurementItemType(StrEnum):
    WINDOW = "window"
    DOOR = "door"

    @property
    def label_uz(self) -> str:
        return {"window": "Oyna", "door": "Eshik"}[self.value]


class RoomType(StrEnum):
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    KIDS_ROOM = "kids_room"
    HALL = "hall"
    CORRIDOR = "corridor"
    BATHROOM = "bathroom"
    OFFICE = "office"
    OTHER = "other"

    @property
    def label_uz(self) -> str:
        return {
            "living_room": "Mehmonxona",
            "bedroom": "Yotoqxona",
            "kitchen": "Oshxona",
            "kids_room": "Bolalar xonasi",
            "hall": "Zal",
            "corridor": "Koridor",
            "bathroom": "Hammom",
            "office": "Ish xonasi",
            "other": "Boshqa",
        }[self.value]


class LocationSource(StrEnum):
    TELEGRAM = "telegram"
    BROWSER = "browser"
    MANUAL = "manual"

    @property
    def label_uz(self) -> str:
        return {
            "telegram": "Telegram",
            "browser": "Brauzer",
            "manual": "Qo'lda kiritilgan",
        }[self.value]


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    STATUS_CHANGE = "status_change"
    UPLOAD = "upload"
