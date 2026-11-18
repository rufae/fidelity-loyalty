"""Plan comercial por comercio y tiendas (merchant_locations).

Revision ID: 0014_plan_locations
Revises: 0013_merchant_ntfy_topic

El plan (`merchants.plan`) define los límites de estructura: tiendas dadas de
alta y programas de fidelización en vivo (catálogo en `domain/plans.py`). Las
tiendas (`merchant_locations`, §11.3) permiten a un comercio con varios
locales operarlos bajo el mismo silo. Todo comercio existente entra en
`basic` por omisión; la ubicación "sede" no se crea automáticamente: el
comercio sin tiendas sigue funcionando como un solo local.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_plan_locations"
down_revision: str | None = "0013_merchant_ntfy_topic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="basic"),
    )
    op.create_table(
        "merchant_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("merchant_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("merchant_locations")
    op.drop_column("merchants", "plan")
