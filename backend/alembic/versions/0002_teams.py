"""Jamoalar (teams): ko'p jamoali izolyatsiya

Nima qo'shiladi:
  * `teams` jadvali;
  * `users.team_id` — foydalanuvchi qaysi jamoada;
  * `projects.team_id` — obyekt qaysi jamoaga tegishli (majburiy).

Mavjud ma'lumotlar «Asosiy jamoa» nomli jamoaga ko'chiriladi, shuning uchun
migratsiya ma'lumot yo'qotmaydi.

Revision ID: 0002_teams
Revises: 0001_initial
Create Date: 2026-07-30

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_teams"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TEAM_NAME = "Asosiy jamoa"


def upgrade() -> None:
    # 1. Jamoalar jadvali
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_teams_name"),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=False)
    op.create_index("ix_teams_is_active", "teams", ["is_active"], unique=False)

    # 2. Ustunlar (avval nullable — mavjud yozuvlarni to'ldirish uchun)
    op.add_column("users", sa.Column("team_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_users_team_id", "users", "teams", ["team_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_users_team_id", "users", ["team_id"], unique=False)
    op.create_index("ix_users_team_role", "users", ["team_id", "role"], unique=False)

    op.add_column("projects", sa.Column("team_id", sa.Uuid(), nullable=True))

    # 3. Mavjud ma'lumotlarni ko'chirish
    connection = op.get_bind()
    has_data = connection.execute(
        sa.text("SELECT 1 FROM projects UNION ALL SELECT 1 FROM users LIMIT 1")
    ).first()

    if has_data:
        team_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO teams (id, name, description, is_active, created_at, updated_at) "
                "VALUES (:id, :name, :description, true, now(), now())"
            ),
            {
                "id": str(team_id),
                "name": DEFAULT_TEAM_NAME,
                "description": "Jamoalar joriy etilishidan oldingi ma'lumotlar shu jamoada.",
            },
        )
        connection.execute(
            sa.text("UPDATE users SET team_id = :team_id WHERE role <> 'admin'"),
            {"team_id": str(team_id)},
        )
        connection.execute(
            sa.text("UPDATE projects SET team_id = :team_id WHERE team_id IS NULL"),
            {"team_id": str(team_id)},
        )

    # 4. Obyekt uchun jamoa majburiy
    op.alter_column("projects", "team_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key(
        "fk_projects_team_id", "projects", "teams", ["team_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index("ix_projects_team_id", "projects", ["team_id"], unique=False)
    op.create_index("ix_projects_team_created", "projects", ["team_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_projects_team_created", table_name="projects")
    op.drop_index("ix_projects_team_id", table_name="projects")
    op.drop_constraint("fk_projects_team_id", "projects", type_="foreignkey")
    op.drop_column("projects", "team_id")

    op.drop_index("ix_users_team_role", table_name="users")
    op.drop_index("ix_users_team_id", table_name="users")
    op.drop_constraint("fk_users_team_id", "users", type_="foreignkey")
    op.drop_column("users", "team_id")

    op.drop_index("ix_teams_is_active", table_name="teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")
