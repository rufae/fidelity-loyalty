"""Diseño de tarjeta del comercio: colores, icono, pie y logotipo (§11.15).

Revision ID: 0016_card_branding
Revises: 0015_password_reset

- `assets`: recursos gráficos validados (logotipo ≤512 KiB, magic bytes).
- `merchant_branding`: uno a uno con el comercio, colores `#RRGGBB`, icono
  del catálogo cerrado, pie de tarjeta y referencia al logotipo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_card_branding"
down_revision: str | None = "0015_password_reset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("merchant_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=40), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "merchant_branding",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "merchant_id",
            sa.Uuid(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("primary_color", sa.String(length=7), nullable=False),
        sa.Column("accent_color", sa.String(length=7), nullable=False),
        sa.Column("stamp_icon", sa.String(length=10), nullable=False),
        sa.Column("footer_text", sa.String(length=80), nullable=True),
        sa.Column(
            "logo_asset_id",
            sa.Uuid(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("merchant_branding")
    op.drop_table("assets")
