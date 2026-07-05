"""final production integration

Revision ID: 202607050001
Revises: 202607040003
Create Date: 2026-07-05 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607050001"
down_revision = "202607040003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("telegram_users", sa.Column("country_code", sa.String(8)))
    op.add_column(
        "telegram_users",
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("telegram_users", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.create_index("ix_telegram_users_last_seen_at", "telegram_users", ["last_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_telegram_users_last_seen_at", table_name="telegram_users")
    op.drop_column("telegram_users", "last_seen_at")
    op.drop_column("telegram_users", "notifications_enabled")
    op.drop_column("telegram_users", "country_code")
