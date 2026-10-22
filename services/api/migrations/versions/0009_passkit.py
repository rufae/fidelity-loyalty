"""Servicio web de actualización de pases Apple (PassKit) y contadores.

Añade:
- `wallet_passes`: `provider_metadata` (JSON) — token de autenticación del
  servicio web de Apple por pase (§6.4); nunca viaja al frontend.
- `background_jobs`: `manual_retries` — reintentos manuales del panel,
  separados de `attempts` automáticos (§15, corrección de la auditoría).
- `pass_device_registrations`: dispositivos registrados para recibir pases
  actualizados (PassKit §6.4).

Revisión ID: 0009_passkit
Down: 0008_lifecycle
Creada: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_passkit"
down_revision: str | None = "0008_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("wallet_passes") as batch:
        batch.add_column(sa.Column("provider_metadata", sa.JSON(), nullable=True))

    with op.batch_alter_table("background_jobs") as batch:
        batch.add_column(
            sa.Column("manual_retries", sa.Integer(), nullable=False, server_default="0")
        )

    op.create_table(
        "pass_device_registrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("device_id", sa.String(length=120), nullable=False),
        sa.Column("pass_type_id", sa.String(length=120), nullable=False),
        sa.Column("serial", sa.String(length=64), nullable=False, index=True),
        sa.Column("membership_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("push_token", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "serial", name="uq_pass_device_serial"),
    )


def downgrade() -> None:
    op.drop_table("pass_device_registrations")
    with op.batch_alter_table("background_jobs") as batch:
        batch.drop_column("manual_retries")
    with op.batch_alter_table("wallet_passes") as batch:
        batch.drop_column("provider_metadata")
