"""durable referral codes

Revision ID: 202607050002
Revises: 202607050001
Create Date: 2026-07-05 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607050002"
down_revision = "202607050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("referral_code", sa.String(64), nullable=True))
    op.execute("UPDATE users SET referral_code = 'rvn_' || replace(id::text, '-', '')")
    op.alter_column("users", "referral_code", nullable=False)
    op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_column("users", "referral_code")
