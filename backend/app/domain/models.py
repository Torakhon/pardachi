"""Domen modellari.

Modellar SQLAlchemy 2.x `DeclarativeBase` asosida yozilgan: ular ham domen
obyektlari, ham persistensiya sxemasi vazifasini bajaradi. Modellarda hech
qanday I/O yoki sessiya logikasi yo'q — barcha bazaviy amallar repozitoriylar
orqali (`app/infrastructure/repositories`) bajariladi.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    AuditAction,
    LocationSource,
    MeasurementItemType,
    ProjectStatus,
    RoomType,
    UserRole,
)

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _enum(enum_cls: type, name: str) -> SAEnum:
    """VARCHAR + CHECK ko'rinishidagi enum (migratsiyalarni soddalashtiradi)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        values_callable=lambda e: [item.value for item in e],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSONVariant,
        Decimal: Numeric(10, 2),
    }


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


class Team(Base, TimestampMixin):
    """Jamoa — ma'lumotlar izolyatsiyasining asosiy chegarasi.

    Har bir obyekt (loyiha) aynan bitta jamoaga tegishli. Jamoa a'zolari faqat
    o'z jamoasining ma'lumotlarini ko'radi; administrator barcha jamoalarni ko'radi.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    # use_alter — `teams` va `users` o'rtasidagi aylanma bog'liqlik uchun
    # (jadval yaratish/o'chirish tartibi buzilmasligi kerak).
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_teams_created_by_id")
    )

    members: Mapped[list[User]] = relationship(
        back_populates="team",
        foreign_keys="User.team_id",
        lazy="selectin",
        order_by="User.first_name",
    )

    @property
    def members_count(self) -> int:
        return len(self.members)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    last_name: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32))
    photo_url: Mapped[str | None] = mapped_column(String(512))
    language_code: Mapped[str] = mapped_column(String(8), default="uz", nullable=False)
    role: Mapped[UserRole] = mapped_column(
        _enum(UserRole, "user_role"), default=UserRole.MEASURER, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    team: Mapped[Team | None] = relationship(
        back_populates="members", foreign_keys=[team_id], lazy="selectin"
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="creator",
        foreign_keys="Project.created_by_id",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
        Index("ix_users_team_role", "team_id", "role"),
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or (self.username or "Foydalanuvchi")

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @property
    def can_write(self) -> bool:
        """Ma'lumot yaratish/tahrirlash huquqi (Ko'ruvchi'da yo'q)."""
        return self.role.can_write

    @property
    def team_name(self) -> str | None:
        return self.team.name if self.team is not None else None


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    order_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        _enum(ProjectStatus, "project_status"),
        default=ProjectStatus.DRAFT,
        nullable=False,
        index=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    team: Mapped[Team] = relationship(foreign_keys=[team_id], lazy="selectin")
    creator: Mapped[User] = relationship(
        back_populates="projects", foreign_keys=[created_by_id], lazy="selectin"
    )
    rooms: Mapped[list[Room]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Room.sort_order, Room.created_at",
        lazy="selectin",
    )
    location: Mapped[ProjectLocation | None] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("order_number", name="uq_projects_order_number"),
        Index("ix_projects_status_created", "status", "created_at"),
        Index("ix_projects_creator_created", "created_by_id", "created_at"),
        Index("ix_projects_team_created", "team_id", "created_at"),
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def rooms_count(self) -> int:
        return len(self.rooms)

    @property
    def items_count(self) -> int:
        return sum(len(room.items) for room in self.rooms)

    @property
    def photos_count(self) -> int:
        return sum(1 for room in self.rooms if room.image is not None)


class ProjectLocation(Base):
    __tablename__ = "project_locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    source: Mapped[LocationSource] = mapped_column(
        _enum(LocationSource, "location_source"), default=LocationSource.BROWSER, nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="location")

    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_location_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_location_longitude"),
    )

    @property
    def maps_url(self) -> str:
        return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    room_type: Mapped[RoomType] = mapped_column(
        _enum(RoomType, "room_type"), default=RoomType.OTHER, nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped[Project] = relationship(back_populates="rooms")
    items: Mapped[list[MeasurementItem]] = relationship(
        back_populates="room",
        cascade="all, delete-orphan",
        order_by="MeasurementItem.sort_order, MeasurementItem.created_at",
        lazy="selectin",
    )
    image: Mapped[RoomImage | None] = relationship(
        back_populates="room",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    __table_args__ = (Index("ix_rooms_project_sort", "project_id", "sort_order"),)

    @property
    def items_count(self) -> int:
        return len(self.items)


class RoomImage(Base):
    __tablename__ = "room_images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    telegram_file_id: Mapped[str | None] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/jpeg")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    room: Mapped[Room] = relationship(back_populates="image")


class MeasurementItem(Base, TimestampMixin):
    __tablename__ = "measurement_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    item_type: Mapped[MeasurementItemType] = mapped_column(
        _enum(MeasurementItemType, "measurement_item_type"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    width_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    curtain_width_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    curtain_height_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    cornice_width_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    cornice_height_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    fabric_type: Mapped[str | None] = mapped_column(String(120))
    curtain_model: Mapped[str | None] = mapped_column(String(120))
    fabric_color: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    room: Mapped[Room] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("width_cm > 0 AND width_cm <= 10000", name="ck_item_width"),
        CheckConstraint("height_cm > 0 AND height_cm <= 10000", name="ck_item_height"),
        CheckConstraint("quantity >= 1 AND quantity <= 100", name="ck_item_quantity"),
        Index("ix_items_room_sort", "room_id", "sort_order"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[AuditAction] = mapped_column(_enum(AuditAction, "audit_action"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id", "created_at"),)
