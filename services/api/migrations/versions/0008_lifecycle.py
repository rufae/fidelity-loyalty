"""Ciclo de vida de membresía, consentimientos y reintentos de trabajos.

Añade:
- `memberships`: `status_reason`, `status_changed_at`, `deletion_requested_at`,
  `anonymized_at` (ADR-0005: suspender ≠ revocar ≠ eliminar).
- `members`: `privacy_notice_version`, `marketing_consent`,
  `marketing_consent_at`, `anonymized_at` (ADR-0006: consentimientos
  registrados; nombre/email obligatorios en altas nuevas).
- `background_jobs`: `next_attempt_at` (reintentos con backoff, §15).

Revisión ID: 0008_lifecycle
Down: 0007_nfc
Creada: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_lifecycle"
down_revision: str | None = "0007_nfc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("memberships") as batch:
        batch.add_column(sa.Column("status_reason", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("members") as batch:
        batch.add_column(sa.Column("privacy_notice_version", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("marketing_consent", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("marketing_consent_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("anonymized_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("background_jobs") as batch:
        batch.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("background_jobs") as batch:
        batch.drop_column("next_attempt_at")
    with op.batch_alter_table("members") as batch:
        batch.drop_column("anonymized_at")
        batch.drop_column("marketing_consent_at")
        batch.drop_column("marketing_consent")
        batch.drop_column("privacy_notice_version")
    with op.batch_alter_table("memberships") as batch:
        batch.drop_column("anonymized_at")
        batch.drop_column("deletion_requested_at")
        batch.drop_column("status_changed_at")
        batch.drop_column("status_reason")
