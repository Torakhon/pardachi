"""Ilova darajasidagi xatoliklar (barcha xabarlar o'zbek tilida)."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Barcha biznes xatoliklarning asosiy klassi."""

    status_code: int = 400
    code: str = "xatolik"
    message: str = "Kutilmagan xatolik yuz berdi."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class NotFoundError(AppError):
    status_code = 404
    code = "topilmadi"
    message = "So'ralgan ma'lumot topilmadi."


class ValidationError(AppError):
    status_code = 422
    code = "notogri_malumot"
    message = "Kiritilgan ma'lumot noto'g'ri."


class ConflictError(AppError):
    status_code = 409
    code = "ziddiyat"
    message = "Bu ma'lumot allaqachon mavjud."


class AuthenticationError(AppError):
    status_code = 401
    code = "avtorizatsiya_xatosi"
    message = "Avtorizatsiyadan o'tilmagan. Iltimos, qaytadan kiring."


class PermissionDeniedError(AppError):
    status_code = 403
    code = "ruxsat_yoq"
    message = "Bu amalni bajarishga ruxsatingiz yo'q."


class InactiveUserError(AppError):
    status_code = 403
    code = "foydalanuvchi_bloklangan"
    message = "Sizning hisobingiz faol emas. Administrator bilan bog'laning."


class StorageError(AppError):
    status_code = 502
    code = "saqlash_xatosi"
    message = "Faylni saqlashda xatolik yuz berdi."


class RateLimitError(AppError):
    status_code = 429
    code = "sorovlar_kop"
    message = "So'rovlar juda ko'p. Biroz kutib qayta urinib ko'ring."
