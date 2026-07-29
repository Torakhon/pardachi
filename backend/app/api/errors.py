"""Xatoliklarni yagona formatda qaytarish (barcha xabarlar o'zbekcha)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Pydantic xato turlarining o'zbekcha tarjimasi
_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "Bu maydonni to'ldirish shart.",
    "string_too_short": "Juda qisqa qiymat kiritildi.",
    "string_too_long": "Juda uzun qiymat kiritildi.",
    "string_type": "Matn kiritilishi kerak.",
    "int_type": "Butun son kiritilishi kerak.",
    "int_parsing": "Butun son kiritilishi kerak.",
    "float_type": "Son kiritilishi kerak.",
    "decimal_parsing": "Raqam noto'g'ri formatda.",
    "decimal_max_places": "Kasr qismi 2 xonadan oshmasligi kerak.",
    "greater_than": "Qiymat noldan katta bo'lishi kerak.",
    "greater_than_equal": "Qiymat juda kichik.",
    "less_than": "Qiymat juda katta.",
    "less_than_equal": "Qiymat juda katta.",
    "uuid_parsing": "Identifikator noto'g'ri.",
    "uuid_type": "Identifikator noto'g'ri.",
    "enum": "Ruxsat etilmagan qiymat tanlandi.",
    "date_from_datetime_parsing": "Sana noto'g'ri formatda (YYYY-MM-DD).",
    "datetime_parsing": "Sana/vaqt noto'g'ri formatda.",
    "value_error": "Kiritilgan qiymat noto'g'ri.",
    "bool_parsing": "Ha/yo'q qiymati kutilgan.",
    "too_short": "Ro'yxat bo'sh bo'lmasligi kerak.",
    "json_invalid": "So'rov tanasi JSON formatida emas.",
}

# HTTP status kodlarining o'zbekcha izohi
_HTTP_MESSAGES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "So'rov noto'g'ri.",
    status.HTTP_401_UNAUTHORIZED: "Avtorizatsiyadan o'tilmagan.",
    status.HTTP_403_FORBIDDEN: "Ruxsat yo'q.",
    status.HTTP_404_NOT_FOUND: "Sahifa yoki ma'lumot topilmadi.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Bu amal qo'llab-quvvatlanmaydi.",
    413: "Yuborilgan fayl juda katta.",
    status.HTTP_429_TOO_MANY_REQUESTS: "So'rovlar juda ko'p. Biroz kutib turing.",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Serverda kutilmagan xatolik yuz berdi.",
}


def _error_response(
    status_code: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def _field_label(location: tuple[Any, ...]) -> str:
    parts = [str(part) for part in location if part not in ("body", "query", "path")]
    return ".".join(parts) or "so'rov"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for error in exc.errors():
            label = _field_label(tuple(error.get("loc", ())))
            error_type = str(error.get("type", ""))
            if error_type == "value_error" and error.get("msg"):
                # Maxsus validatorlardan kelgan o'zbekcha xabar
                message = str(error["msg"]).removeprefix("Value error, ")
            else:
                message = _VALIDATION_MESSAGES.get(error_type, "Kiritilgan qiymat noto'g'ri.")
            fields[label] = message

        return _error_response(
            422,
            "notogri_malumot",
            "Ma'lumotlar to'liq yoki to'g'ri kiritilmagan.",
            {"fields": fields},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _HTTP_MESSAGES.get(exc.status_code)
        if message is None:
            message = str(exc.detail) if exc.detail else "Xatolik yuz berdi."
        return _error_response(exc.status_code, f"http_{exc.status_code}", message)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Bazadagi yaxlitlik xatosi: %s", exc)
        return _error_response(
            status.HTTP_409_CONFLICT,
            "ziddiyat",
            "Ma'lumotni saqlab bo'lmadi: bunday yozuv allaqachon mavjud yoki bog'liqlik buzilgan.",
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Baza xatosi", exc_info=exc)
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "baza_xatosi",
            "Ma'lumotlar bazasi bilan bog'lanishda xatolik. Birozdan so'ng urinib ko'ring.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Kutilmagan xatolik", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "server_xatosi",
            _HTTP_MESSAGES[status.HTTP_500_INTERNAL_SERVER_ERROR],
        )
