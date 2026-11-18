"""Tema ntfy propio de cada comercio para los avisos de soporte.

Revision ID: 0013_merchant_ntfy_topic
Revises: 0012_membership_origin

Cuando la plataforma responde en una conversación, el comercio puede recibir
un aviso push (Plan.md §11). Cada comercio tiene su **propio** tema ntfy,
generado con aleatoriedad criptográfica: en ntfy el nombre del tema actúa de
credencial, así que no puede derivarse del slug (sería adivinable, §5.2).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_merchant_ntfy_topic"
down_revision: str | None = "0012_membership_origin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column("support_ntfy_topic", sa.String(length=40), nullable=True),
    )
    op.create_unique_constraint(
        "uq_merchant_support_ntfy_topic",
        "merchants",
        ["support_ntfy_topic"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_merchant_support_ntfy_topic", "merchants", type_="unique")
    op.drop_column("merchants", "support_ntfy_topic")
