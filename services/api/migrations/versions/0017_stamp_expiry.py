"""Caducidad opcional de sellos (decisión de compra #6, §7.7).

Revision ID: 0017_stamp_expiry
Revises: 0016_card_branding

- `loyalty_programs.stamps_expire_days`: regla opcional (días); NULL por
  defecto = sin caducidad, como hasta ahora.
- `loyalty_transactions.expires_at`: fecha de caducidad del lote `earn`;
  solo se rellena cuando el programa define la regla. El vencimiento se
  materializa después como un movimiento `expiry` (nunca se borra el earn).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_stamp_expiry"
down_revision: str | None = "0016_card_branding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "loyalty_programs",
        sa.Column("stamps_expire_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "loyalty_transactions",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Vencidos pendientes: localizar los lotes caducados por membresía.
    op.create_index(
        "ix_loyalty_transactions_expires_at",
        "loyalty_transactions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_loyalty_transactions_expires_at", table_name="loyalty_transactions")
    op.drop_column("loyalty_transactions", "expires_at")
    op.drop_column("loyalty_programs", "stamps_expire_days")
