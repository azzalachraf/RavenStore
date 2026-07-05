"""payment and fulfillment automation

Revision ID: 202607040001
Revises: 202607030001
Create Date: 2026-07-04 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607040001"
down_revision = "202607030001"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.execute(
        "DELETE FROM idempotency_keys a USING idempotency_keys b "
        "WHERE a.key = b.key AND (a.created_at, a.id) < (b.created_at, b.id)"
    )
    op.drop_constraint("uq_idempotency_key_user", "idempotency_keys", type_="unique")
    op.create_unique_constraint("uq_idempotency_keys_key", "idempotency_keys", ["key"])

    op.add_column("inventory", sa.Column("quantity_delivered", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("inventory", sa.Column("unlimited_stock", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("inventory", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    op.add_column("payments", sa.Column("provider_order_id_encrypted", sa.Text()))
    op.add_column("payments", sa.Column("payment_reference_hash", sa.String(64)))
    op.execute("UPDATE payments SET payment_reference_hash = encode(sha256(payment_reference_encrypted::bytea), 'hex')")
    op.alter_column("payments", "payment_reference_hash", nullable=False)
    op.create_unique_constraint("uq_payments_reference_hash", "payments", ["payment_reference_hash"])
    op.add_column("payments", sa.Column("payment_url", sa.Text()))
    op.add_column("payments", sa.Column("confirmed_at", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("failed_at", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("manual_review_reason", sa.String(255)))
    op.add_column("transactions", sa.Column("reference_hash", sa.String(64)))
    op.create_index("ix_transactions_reference_hash", "transactions", ["reference_hash"])

    op.add_column("payment_verifications", sa.Column("locked_at", sa.DateTime(timezone=True)))
    op.add_column("payment_verifications", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("payment_verifications", sa.Column("failure_code", sa.String(120)))
    op.add_column("payment_verifications", sa.Column("submitted_reference_encrypted", sa.Text()))
    op.add_column("payment_verifications", sa.Column("submitted_reference_hash", sa.String(64)))
    op.create_index("ix_payment_verifications_reference_hash", "payment_verifications", ["submitted_reference_hash"])
    op.execute(
        "DELETE FROM payment_verifications a USING payment_verifications b "
        "WHERE a.payment_id = b.payment_id AND (a.created_at, a.id) < (b.created_at, b.id)"
    )
    op.create_unique_constraint("uq_payment_verifications_payment_id", "payment_verifications", ["payment_id"])

    op.add_column("delivery_queue", sa.Column("provider_key", sa.String(120)))
    op.add_column("delivery_queue", sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.add_column("delivery_queue", sa.Column("last_error", sa.Text()))
    op.execute(
        "DELETE FROM delivery_queue a USING delivery_queue b "
        "WHERE a.order_item_id = b.order_item_id AND (a.created_at, a.id) < (b.created_at, b.id)"
    )
    op.create_unique_constraint("uq_delivery_queue_order_item", "delivery_queue", ["order_item_id"])

    op.add_column("webhook_logs", sa.Column("external_event_id", sa.String(255)))
    op.add_column("webhook_logs", sa.Column("payload_hash", sa.String(64)))
    op.create_unique_constraint("uq_webhook_logs_external_event_id", "webhook_logs", ["external_event_id"])

    op.add_column("notifications", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notifications", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("notifications", sa.Column("last_error", sa.Text()))

    op.create_table(
        "inventory_pools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("delivery_type", sa.String(48), nullable=False),
        sa.Column("provider_key", sa.String(120)),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("unlimited_stock", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="5"),
        *_timestamps(),
    )
    op.create_index("ix_inventory_pools_variant_active", "inventory_pools", ["product_variant_id", "is_active", "priority"])

    op.create_table(
        "inventory_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_pools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payload_encrypted", sa.Text(), nullable=False),
        sa.Column("payload_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="available"),
        sa.Column("reserved_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column("reserved_order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("order_items.id", ondelete="SET NULL"), unique=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
        sa.UniqueConstraint("pool_id", "payload_fingerprint", name="uq_inventory_asset_fingerprint"),
    )
    op.create_index("ix_inventory_assets_pool_status", "inventory_assets", ["pool_id", "status", "created_at"])

    op.create_table(
        "inventory_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("pool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_pools.id", ondelete="SET NULL")),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inventory_assets.id", ondelete="SET NULL"), unique=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="reserved"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_inventory_reservations_status_expires", "inventory_reservations", ["status", "expires_at"])

    op.create_table(
        "payment_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payment_verifications.id", ondelete="SET NULL")),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submitted_reference_hash", sa.String(64)),
        sa.Column("failure_code", sa.String(120)),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("provider_response", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )
    op.create_index("ix_payment_attempts_payment_created", "payment_attempts", ["payment_id", "created_at"])
    op.create_index("ix_payment_attempts_status_created", "payment_attempts", ["status", "created_at"])

    op.create_table(
        "fraud_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_fraud_signals_payment_severity", "fraud_signals", ["payment_id", "severity"])

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("invoice_number", sa.String(40), nullable=False, unique=True),
        sa.Column("subtotal_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(12), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )
    op.create_table(
        "receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="SET NULL")),
        sa.Column("receipt_number", sa.String(40), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(18, 8), nullable=False),
        sa.Column("currency", sa.String(12), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_timestamps(),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_outbox_events_status_available", "outbox_events", ["status", "available_at"])
    op.create_index("ix_outbox_events_aggregate", "outbox_events", ["aggregate_type", "aggregate_id"])


def downgrade() -> None:
    for table in ["outbox_events", "receipts", "invoices", "fraud_signals", "payment_attempts", "inventory_reservations", "inventory_assets", "inventory_pools"]:
        op.drop_table(table)
    op.drop_constraint("uq_webhook_logs_external_event_id", "webhook_logs", type_="unique")
    op.drop_column("webhook_logs", "payload_hash")
    op.drop_column("webhook_logs", "external_event_id")
    for column in ["last_error", "next_attempt_at", "attempt_count"]:
        op.drop_column("notifications", column)
    op.drop_constraint("uq_delivery_queue_order_item", "delivery_queue", type_="unique")
    for column in ["last_error", "completed_at", "provider_key"]:
        op.drop_column("delivery_queue", column)
    op.drop_constraint("uq_payment_verifications_payment_id", "payment_verifications", type_="unique")
    op.drop_index("ix_payment_verifications_reference_hash", table_name="payment_verifications")
    for column in ["submitted_reference_hash", "submitted_reference_encrypted", "failure_code", "completed_at", "locked_at"]:
        op.drop_column("payment_verifications", column)
    op.drop_constraint("uq_payments_reference_hash", "payments", type_="unique")
    for column in ["manual_review_reason", "risk_score", "failed_at", "confirmed_at", "payment_url", "payment_reference_hash", "provider_order_id_encrypted"]:
        op.drop_column("payments", column)
    op.drop_index("ix_transactions_reference_hash", table_name="transactions")
    op.drop_column("transactions", "reference_hash")
    for column in ["is_active", "unlimited_stock", "quantity_delivered"]:
        op.drop_column("inventory", column)
    op.drop_constraint("uq_idempotency_keys_key", "idempotency_keys", type_="unique")
    op.create_unique_constraint("uq_idempotency_key_user", "idempotency_keys", ["key", "user_id"])
