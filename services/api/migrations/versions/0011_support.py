"""Soporte B2B: conversaciones, mensajes, llamadas y avisos."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_support"
down_revision: str | None = "0010_member_card_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("preferred_contact", sa.String(length=20), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("merchant_id", "idempotency_key", name="uq_support_thread_idem"),
    )
    op.create_index("ix_support_threads_merchant_id", "support_threads", ["merchant_id"])
    op.create_index(
        "ix_support_threads_created_by_user_id", "support_threads", ["created_by_user_id"]
    )
    op.create_index("ix_support_threads_status", "support_threads", ["status"])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "thread_id",
            sa.Uuid(),
            sa.ForeignKey("support_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_type", sa.String(length=20), nullable=False),
        sa.Column(
            "author_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("read_by_merchant_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_by_platform_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("thread_id", "idempotency_key", name="uq_support_message_idem"),
    )
    op.create_index("ix_support_messages_thread_id", "support_messages", ["thread_id"])
    op.create_index("ix_support_messages_merchant_id", "support_messages", ["merchant_id"])
    op.create_index("ix_support_messages_author_user_id", "support_messages", ["author_user_id"])

    op.create_table(
        "support_callback_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "thread_id",
            sa.Uuid(),
            sa.ForeignKey("support_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_encrypted", sa.String(length=512), nullable=False),
        sa.Column("availability", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column(
            "requested_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("thread_id", "idempotency_key", name="uq_support_callback_idem"),
    )
    op.create_index(
        "ix_support_callback_requests_thread_id", "support_callback_requests", ["thread_id"]
    )
    op.create_index(
        "ix_support_callback_requests_merchant_id", "support_callback_requests", ["merchant_id"]
    )
    op.create_index("ix_support_callback_requests_status", "support_callback_requests", ["status"])

    op.create_table(
        "support_notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "thread_id",
            sa.Uuid(),
            sa.ForeignKey("support_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.Uuid(),
            sa.ForeignKey("support_messages.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manual_retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("error_code", sa.String(length=60), nullable=True),
        sa.Column("error_detail", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_support_notification_idem"),
    )
    op.create_index("ix_support_notifications_thread_id", "support_notifications", ["thread_id"])
    op.create_index("ix_support_notifications_message_id", "support_notifications", ["message_id"])
    op.create_index("ix_support_notifications_status", "support_notifications", ["status"])


def downgrade() -> None:
    op.drop_table("support_notifications")
    op.drop_table("support_callback_requests")
    op.drop_table("support_messages")
    op.drop_table("support_threads")
