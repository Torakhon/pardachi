"""FastAPI ilovasining kirish nuqtasi."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.middleware import (
    OriginGuardMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.infrastructure.db.session import dispose_engine

setup_logging(settings.log_level, json_logs=settings.is_production)
logger = get_logger(__name__)

DESCRIPTION = """
**Pardachi** — parda o'lchovlarini raqamlashtirish uchun Telegram Mini App backend API.

### Rollar
* **Administrator** — barcha obyektlar, o'lchovlar va foydalanuvchilarni boshqaradi.
* **O'lchovchi** — o'z obyektlarini yaratadi va tahrirlaydi.

### Avtorizatsiya
1. Mini App `initData` qatorini `POST /api/v1/auth/telegram` ga yuboradi.
2. Javobdagi `access_token` barcha so'rovlarda `Authorization: Bearer <token>` sifatida yuboriladi.
3. Muddati tugasa `POST /api/v1/auth/refresh` orqali yangilanadi.

### Oflayn rejim
Obyekt, xona va o'lchov yaratishda mijoz o'zi generatsiya qilgan `id` (UUID) ni yuborishi mumkin.
Bir xil `id` bilan kelgan takroriy so'rov yangi yozuv yaratmaydi — bu internet uzilganda
lokal saqlangan ma'lumotlarni xavfsiz sinxronlash imkonini beradi.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Pardachi API ishga tushdi (muhit=%s, saqlagich=%s)",
        settings.environment,
        settings.storage_backend,
    )
    yield
    await dispose_engine()
    logger.info("Pardachi API to'xtatildi")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "Pardachi", "url": "https://t.me/" + (settings.telegram_bot_username or "")},
        license_info={"name": "MIT"},
    )

    # Middleware (oxirgi qo'shilgani birinchi ishlaydi)
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(OriginGuardMiddleware, config=settings)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.cors_allow_all else settings.cors_origins,
        allow_credentials=not settings.cors_allow_all,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
        max_age=600,
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    if settings.storage_backend == "local":
        app.mount(
            settings.media_url_prefix,
            StaticFiles(directory=settings.media_root, check_dir=False),
            name="media",
        )

    app.openapi = lambda: _custom_openapi(app)  # type: ignore[method-assign]
    return app


def _custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"].setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "`POST /api/v1/auth/telegram` orqali olingan access token.",
    }
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            if isinstance(operation, dict) and not path.endswith(
                ("/auth/telegram", "/auth/refresh", "/auth/dev-login", "/health", "/meta/enums")
            ):
                operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = schema
    return schema


app = create_app()
