"""Recuperación de contraseña de personal (§8.3).

Revision ID: 0015_password_reset
Revises: 0014_plan_locations

Tabla `password_reset_tokens`: enlaces de un solo uso, caducan en 30 minutos
y se guardan hasheados. Al confirmar el cambio se invalidan todas las
sesiones del usuario (§8.3: rotación tras cambio de credenciales).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_password_reset"
down_revision: str | None = "0014_plan_locations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
