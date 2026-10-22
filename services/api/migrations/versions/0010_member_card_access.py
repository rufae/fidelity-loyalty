"""Verificación de correo y sesiones para recuperar tarjetas de cliente."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_member_card_access"
down_revision: str | None = "0009_passkit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "member_email_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "member_id", sa.Uuid(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "membership_id",
            sa.Uuid(),
            sa.ForeignKey("memberships.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_member_email_tokens_member_id", "member_email_tokens", ["member_id"])
    op.create_index("ix_member_email_tokens_merchant_id", "member_email_tokens", ["merchant_id"])
    op.create_index("ix_member_email_tokens_token_hash", "member_email_tokens", ["token_hash"])

    op.create_table(
        "member_card_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "member_id", sa.Uuid(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_member_card_sessions_member_id", "member_card_sessions", ["member_id"])
    op.create_index("ix_member_card_sessions_merchant_id", "member_card_sessions", ["merchant_id"])
    op.create_index("ix_member_card_sessions_token_hash", "member_card_sessions", ["token_hash"])


def downgrade() -> None:
    op.drop_table("member_card_sessions")
    op.drop_table("member_email_tokens")
    with op.batch_alter_table("members") as batch:
        batch.drop_column("email_verified_at")
