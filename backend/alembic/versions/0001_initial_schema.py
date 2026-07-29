"""Boshlang'ich sxema: foydalanuvchilar, obyektlar, xonalar, rasmlar, o'lchovlar, audit

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=32)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("language_code", sa.String(length=8), nullable=False),
        sa.Column("role", _enum("admin", "measurer", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_role_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=400), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            _enum("draft", "in_progress", "completed", "cancelled", name="project_status"),
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number", name="uq_projects_order_number"),
    )
    op.create_index("ix_projects_name", "projects", ["name"], unique=False)
    op.create_index("ix_projects_order_number", "projects", ["order_number"], unique=False)
    op.create_index("ix_projects_customer_name", "projects", ["customer_name"], unique=False)
    op.create_index("ix_projects_customer_phone", "projects", ["customer_phone"], unique=False)
    op.create_index("ix_projects_status", "projects", ["status"], unique=False)
    op.create_index("ix_projects_created_by_id", "projects", ["created_by_id"], unique=False)
    op.create_index("ix_projects_deleted_at", "projects", ["deleted_at"], unique=False)
    op.create_index("ix_projects_status_created", "projects", ["status", "created_at"], unique=False)
    op.create_index("ix_projects_creator_created", "projects", ["created_by_id", "created_at"], unique=False)

    op.create_table(
        "project_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("accuracy_m", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column(
            "source",
            _enum("telegram", "browser", "manual", name="location_source"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_location_latitude"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_location_longitude"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "room_type",
            _enum(
                "living_room",
                "bedroom",
                "kitchen",
                "kids_room",
                "hall",
                "corridor",
                "bathroom",
                "office",
                "other",
                name="room_type",
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rooms_project_id", "rooms", ["project_id"], unique=False)
    op.create_index("ix_rooms_project_sort", "rooms", ["project_id", "sort_order"], unique=False)

    op.create_table(
        "room_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=400), nullable=False),
        sa.Column("url", sa.String(length=600), nullable=False),
        sa.Column("telegram_file_id", sa.String(length=256), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id"),
    )

    op.create_table(
        "measurement_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "item_type",
            _enum("window", "door", name="measurement_item_type"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("width_cm", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("height_cm", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("curtain_width_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("curtain_height_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("cornice_width_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("cornice_height_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("fabric_type", sa.String(length=120), nullable=True),
        sa.Column("curtain_model", sa.String(length=120), nullable=True),
        sa.Column("fabric_color", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("width_cm > 0 AND width_cm <= 10000", name="ck_item_width"),
        sa.CheckConstraint("height_cm > 0 AND height_cm <= 10000", name="ck_item_height"),
        sa.CheckConstraint("quantity >= 1 AND quantity <= 100", name="ck_item_quantity"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_measurement_items_room_id", "measurement_items", ["room_id"], unique=False)
    op.create_index("ix_measurement_items_item_type", "measurement_items", ["item_type"], unique=False)
    op.create_index("ix_items_room_sort", "measurement_items", ["room_id", "sort_order"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "action",
            _enum("create", "update", "delete", "login", "status_change", "upload", name="audit_action"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"], unique=False)
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("measurement_items")
    op.drop_table("room_images")
    op.drop_table("rooms")
    op.drop_table("project_locations")
    op.drop_table("projects")
    op.drop_table("users")
