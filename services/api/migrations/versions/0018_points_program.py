"""Modo puntos por importe (mejora de compra #9, §7.1 y §7.6).

- `loyalty_programs.points_per_euro`: regla entera de puntos por euro.
  NULL por defecto; obligatoria antes de publicar un programa `points`.
- El importe lo teclea el personal (MVP sin integración de TPV, §7.6) y
  el backend calcula los puntos en Decimal con redondeo hacia abajo: el
  navegador nunca envía la cantidad de puntos a otorgar.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_points_program"
down_revision: str | None = "0017_stamp_expiry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "loyalty_programs",
        sa.Column("points_per_euro", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("loyalty_programs", "points_per_euro")
