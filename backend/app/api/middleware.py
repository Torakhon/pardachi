"""HTTP middleware: so'rov konteksti, xavfsizlik sarlavhalari, oddiy rate-limit."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.logging import get_logger, log_extra, new_request_id, request_id_ctx, user_id_ctx

logger = get_logger("app.request")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Har bir so'rovga ID beradi, davomiyligini o'lchaydi va loglaydi."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or new_request_id()
        request_id_ctx.set(request_id)
        user_id_ctx.set("-")
        started = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        if not request.url.path.startswith(("/media", "/docs", "/openapi", "/redoc")):
            logger.info(
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
                extra=log_extra(
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    duration_ms=duration_ms,
                ),
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """XSS/clickjacking va MIME-sniffing himoyasi uchun sarlavhalar."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; img-src 'self' data:",
        )
        response.headers.setdefault("Permissions-Policy", "geolocation=(self), camera=(self)")
        return response


class OriginGuardMiddleware(BaseHTTPMiddleware):
    """CSRF-ga qarshi qo'shimcha qatlam.

    API Bearer token bilan ishlaydi (cookie ishlatilmaydi), shuning uchun klassik
    CSRF hujumi amalda ishlamaydi. Shunga qaramay, holatni o'zgartiruvchi
    so'rovlarda `Origin` sarlavhasi ruxsat etilgan ro'yxatga tekshiriladi.
    """

    def __init__(self, app: object, config: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._config = config

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if (
            request.method not in SAFE_METHODS
            and not self._config.cors_allow_all
            and (origin := request.headers.get("origin"))
            and origin not in self._config.cors_origins
        ):
            logger.warning("Ruxsat etilmagan Origin: %s", origin)
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "notogri_manba",
                        "message": "So'rov ruxsat etilmagan manbadan yuborildi.",
                        "details": {},
                    }
                },
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Oddiy xotiradagi rate-limiter (IP + yo'l bo'yicha, siljuvchi oyna)."""

    def __init__(self, app: object, limit_per_minute: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._limit = limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if self._limit <= 0 or request.url.path.startswith(("/media", "/docs", "/openapi")):
            return await call_next(request)

        client = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client:
            client = request.client.host if request.client else "unknown"

        now = time.monotonic()
        window = self._hits[client]
        while window and now - window[0] > 60:
            window.popleft()

        if len(window) >= self._limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "sorovlar_kop",
                        "message": "So'rovlar juda ko'p. Biroz kutib qayta urinib ko'ring.",
                        "details": {},
                    }
                },
                headers={"Retry-After": "30"},
            )

        window.append(now)
        if len(self._hits) > 10_000:  # xotira o'sib ketmasligi uchun tozalash
            for key in [k for k, v in self._hits.items() if not v or now - v[-1] > 300]:
                self._hits.pop(key, None)

        return await call_next(request)
