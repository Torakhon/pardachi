"""v1 API marshrutlarini yig'ish."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, measurements, projects, rooms, stats, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(rooms.router)
api_router.include_router(measurements.router)
api_router.include_router(users.router)
api_router.include_router(stats.router)
