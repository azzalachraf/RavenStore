"""real-time synchronization and event delivery

Revision ID: 202607040002
Revises: 202607040001
Create Date: 2026-07-04 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607040002"
down_revision = "202607040001"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("topic", sa.String(80), nullable=False, server_default="system"))
    op.add_column("outbox_events", sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("outbox_events", sa.Column("partition_key", sa.String(160)))
    op.execute("UPDATE outbox_events SET partition_key = aggregate_type || ':' || aggregate_id::text")
    op.alter_column("outbox_events", "partition_key", nullable=False)
    op.add_column("outbox_events", sa.Column("audience", sa.String(32), nullable=False, server_default="internal"))
    op.add_column("outbox_events", sa.Column("correlation_id", sa.String(120)))
    op.add_column("outbox_events", sa.Column("causation_id", sa.String(120)))
    op.add_column("outbox_events", sa.Column("trace_id", sa.String(120)))
    op.add_column("outbox_events", sa.Column("cache_tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("outbox_events", sa.Column("claimed_at", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("claimed_by", sa.String(160)))
    op.add_column("outbox_events", sa.Column("published_at", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("dead_lettered_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE outbox_events SET topic = split_part(event_type, '.', 1)")
    op.execute(
        "UPDATE outbox_events SET audience = 'customer' "
        "WHERE topic IN ('order', 'payment', 'delivery', 'support', 'referral')"
    )
    op.execute("UPDATE outbox_events SET audience = 'admin' WHERE topic = 'inventory'")
    op.create_index("ix_outbox_events_topic", "outbox_events", ["topic"])
    op.create_index("ix_outbox_events_partition_key", "outbox_events", ["partition_key"])
    op.create_index("ix_outbox_events_correlation_id", "outbox_events", ["correlation_id"])
    op.create_index("ix_outbox_events_trace_id", "outbox_events", ["trace_id"])

    op.add_column("notifications", sa.Column("source_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbox_events.id", ondelete="SET NULL")))
    op.create_index("ix_notifications_source_event_id", "notifications", ["source_event_id"])
    op.create_unique_constraint(
        "uq_notification_event_user_channel",
        "notifications",
        ["source_event_id", "user_id", "channel"],
    )

    op.create_table(
        "event_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbox_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("external_id", sa.String(255)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("outbox_event_id", "destination", name="uq_event_delivery_destination"),
    )
    op.create_index("ix_event_deliveries_event", "event_deliveries", ["outbox_event_id"])
    op.create_index("ix_event_deliveries_status", "event_deliveries", ["status", "created_at"])

    op.create_table(
        "event_consumer_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("last_stream_id", sa.String(80)),
        sa.Column("status", sa.String(32), nullable=False, server_default="healthy"),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )

    op.create_table(
        "cache_invalidation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("outbox_events.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("cache_invalidation_logs")
    op.drop_table("event_consumer_checkpoints")
    op.drop_table("event_deliveries")
    op.drop_constraint("uq_notification_event_user_channel", "notifications", type_="unique")
    op.drop_index("ix_notifications_source_event_id", table_name="notifications")
    op.drop_column("notifications", "source_event_id")
    for index in [
        "ix_outbox_events_trace_id",
        "ix_outbox_events_correlation_id",
        "ix_outbox_events_partition_key",
        "ix_outbox_events_topic",
    ]:
        op.drop_index(index, table_name="outbox_events")
    for column in [
        "dead_lettered_at",
        "published_at",
        "claimed_by",
        "claimed_at",
        "cache_tags",
        "trace_id",
        "causation_id",
        "correlation_id",
        "audience",
        "partition_key",
        "schema_version",
        "topic",
    ]:
        op.drop_column("outbox_events", column)
