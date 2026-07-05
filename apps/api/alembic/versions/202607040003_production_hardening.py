"""security, monitoring and production hardening

Revision ID: 202607040003
Revises: 202607040002
Create Date: 2026-07-04 00:00:03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607040003"
down_revision = "202607040002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_users_locked_until", "users", ["locked_until"])

    op.add_column("admin_profiles", sa.Column("mfa_secret_encrypted", sa.Text()))
    op.add_column("admin_profiles", sa.Column("mfa_recovery_codes_encrypted", sa.Text()))
    op.add_column("admin_profiles", sa.Column("mfa_verified_at", sa.DateTime(timezone=True)))

    op.add_column("refresh_tokens", sa.Column("token_id", sa.String(128)))
    op.add_column("refresh_tokens", sa.Column("session_id", postgresql.UUID(as_uuid=True)))
    op.add_column("refresh_tokens", sa.Column("last_used_at", sa.DateTime(timezone=True)))
    op.add_column("refresh_tokens", sa.Column("reused_at", sa.DateTime(timezone=True)))
    op.add_column("refresh_tokens", sa.Column("created_ip_hash", sa.String(64)))
    op.add_column("refresh_tokens", sa.Column("user_agent", sa.String(512)))
    op.execute("UPDATE refresh_tokens SET token_id = id::text, session_id = id")
    op.alter_column("refresh_tokens", "token_id", nullable=False)
    op.alter_column("refresh_tokens", "session_id", nullable=False)
    op.create_unique_constraint("uq_refresh_tokens_token_id", "refresh_tokens", ["token_id"])
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"])

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("ip_hash", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("trace_id", sa.String(120)),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_events_actor", "security_events", ["actor_user_id"])
    op.create_index("ix_security_events_type_created", "security_events", ["event_type", "created_at"])
    op.create_index("ix_security_events_severity", "security_events", ["severity"])
    op.create_index("ix_security_events_outcome", "security_events", ["outcome"])
    op.create_index("ix_security_events_ip_hash", "security_events", ["ip_hash"])
    op.create_index("ix_security_events_trace_id", "security_events", ["trace_id"])

    op.execute("""
        CREATE FUNCTION ravenstore_reject_audit_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'immutable audit records cannot be modified';
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table in ("activity_logs", "security_events", "webhook_logs"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION ravenstore_reject_audit_mutation()"
        )


def downgrade() -> None:
    for table in ("webhook_logs", "security_events", "activity_logs"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS ravenstore_reject_audit_mutation")
    op.drop_table("security_events")
    op.drop_index("ix_refresh_tokens_session_id", table_name="refresh_tokens")
    op.drop_constraint("uq_refresh_tokens_token_id", "refresh_tokens", type_="unique")
    for column in ("user_agent", "created_ip_hash", "reused_at", "last_used_at", "session_id", "token_id"):
        op.drop_column("refresh_tokens", column)
    for column in ("mfa_verified_at", "mfa_recovery_codes_encrypted", "mfa_secret_encrypted"):
        op.drop_column("admin_profiles", column)
    op.drop_index("ix_users_locked_until", table_name="users")
    for column in ("password_changed_at", "locked_until", "failed_login_attempts"):
        op.drop_column("users", column)
