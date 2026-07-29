"""Xona rasmlari bilan ishlash (yuklash, siqish, almashtirish)."""

from __future__ import annotations

import asyncio
import hashlib
import io
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from app.application.permissions import ensure_can_edit_project, ensure_can_view_project
from app.core.config import Settings, settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger, log_extra
from app.domain.enums import AuditAction, ProjectStatus
from app.domain.models import Project, Room, RoomImage, User
from app.domain.repositories import UnitOfWork
from app.infrastructure.storage.base import FileStorage, StoredFile

logger = get_logger(__name__)


class ImageService:
    def __init__(self, uow: UnitOfWork, storage: FileStorage, config: Settings | None = None) -> None:
        self._uow = uow
        self._storage = storage
        self._config = config or settings

    async def get_for_room(self, room_id: uuid.UUID, actor: User) -> RoomImage:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_view_project(actor, project)
        image = await self._uow.images.get_by_room(room_id)
        if image is None:
            raise NotFoundError("Bu xonaga rasm yuklanmagan.")
        return image

    async def upload(
        self,
        room_id: uuid.UUID,
        *,
        content: bytes,
        content_type: str,
        actor: User,
    ) -> RoomImage:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        self._validate(content, content_type)
        processed, width, height = await asyncio.to_thread(self._process_image, content)
        checksum = hashlib.sha256(processed).hexdigest()

        old_image = await self._uow.images.get_by_room(room_id)
        old_key = old_image.storage_key if old_image is not None else None

        stored: StoredFile = await self._storage.save(
            processed,
            filename=f"{room_id}-{uuid.uuid4().hex[:8]}.jpg",
            content_type="image/jpeg",
            width=width,
            height=height,
            checksum=checksum,
            caption=f"{project.name} — {room.name}",
        )

        if old_image is not None:
            await self._uow.images.delete(old_image)
            await self._uow.flush()

        image = RoomImage(
            room_id=room_id,
            storage_key=stored.storage_key,
            url=stored.url,
            telegram_file_id=stored.telegram_file_id,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            width=stored.width,
            height=stored.height,
            checksum=stored.checksum,
            uploaded_by_id=actor.id,
        )
        await self._uow.images.add(image)

        project.updated_by_id = actor.id
        if project.status is ProjectStatus.DRAFT:
            project.status = ProjectStatus.IN_PROGRESS

        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.UPLOAD,
            entity_type="room_image",
            entity_id=str(image.id),
            payload={"room_id": str(room_id), "size": image.size_bytes, "replaced": old_key is not None},
        )
        await self._uow.commit()

        if old_key:
            await self._storage.delete(old_key)

        logger.info(
            "Xona rasmi yuklandi",
            extra=log_extra(room_id=str(room_id), size=image.size_bytes),
        )
        return image

    async def delete(self, room_id: uuid.UUID, actor: User) -> None:
        room = await self._require_room(room_id)
        project = await self._require_project(room.project_id)
        ensure_can_edit_project(actor, project)

        image = await self._uow.images.get_by_room(room_id)
        if image is None:
            raise NotFoundError("Bu xonaga rasm yuklanmagan.")

        storage_key = image.storage_key
        await self._uow.images.delete(image)
        await self._uow.audit.add(
            actor_id=actor.id,
            action=AuditAction.DELETE,
            entity_type="room_image",
            entity_id=str(image.id),
            payload={"room_id": str(room_id)},
        )
        await self._uow.commit()
        await self._storage.delete(storage_key)

    # ------------------------------------------------------------ internal

    def _validate(self, content: bytes, content_type: str) -> None:
        if not content:
            raise ValidationError("Rasm fayli bo'sh.")
        if len(content) > self._config.max_upload_size_bytes:
            raise ValidationError(f"Rasm hajmi {self._config.max_upload_size_mb} MB dan oshmasligi kerak.")
        normalized = (content_type or "").split(";")[0].strip().lower()
        if normalized not in self._config.allowed_image_types:
            raise ValidationError("Faqat JPG, PNG yoki WEBP formatdagi rasm yuklash mumkin.")

    def _process_image(self, content: bytes) -> tuple[bytes, int, int]:
        """Rasmni JPEG ga o'giradi, o'lchamini kichiraytiradi va EXIF ni tozalaydi."""
        try:
            with Image.open(io.BytesIO(content)) as source:
                source.load()
                image = ImageOps.exif_transpose(source)
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                max_side = self._config.image_max_dimension
                if max(image.size) > max_side:
                    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                image.save(
                    buffer,
                    format="JPEG",
                    quality=self._config.image_quality,
                    optimize=True,
                    progressive=True,
                )
                return buffer.getvalue(), image.width, image.height
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValidationError("Rasmni o'qib bo'lmadi. Boshqa fayl tanlang.") from exc

    async def _require_room(self, room_id: uuid.UUID) -> Room:
        room = await self._uow.rooms.get(room_id)
        if room is None:
            raise NotFoundError("Xona topilmadi.")
        return room

    async def _require_project(self, project_id: uuid.UUID) -> Project:
        project = await self._uow.projects.get(project_id)
        if project is None:
            raise NotFoundError("Obyekt topilmadi.")
        return project
