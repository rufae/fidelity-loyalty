"""Origen de la membresía: pública (verifica email) o mostrador (alta presencial).

Revision ID: 0012_membership_origin
Revises: 0011_support

El mostrador emite tarjetas en persona (§13.5): el ancla de confianza es la
entrega presencial, no el buzón. El email registrado en el mostrador queda
sin verificar a propósito y **no bloquea** la tarjeta; en el alta pública la
verificación sigue siendo obligatoria (ADR-0006).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_membership_origin"
down_revision: str | None = "0011_support"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memberships",
        sa.Column(
            "origin",
            sa.String(length=20),
            nullable=False,
            server_default="public",
        ),
    )


def downgrade() -> None:
    op.drop_column("memberships", "origin")
