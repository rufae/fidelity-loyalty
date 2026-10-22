"""Baseline de esquema — FASE 1.

La FASE 1 no define entidades de producto: este primer revision deja
establecida la línea base de Alembic (`alembic_version`) para que
`alembic upgrade head` y `alembic downgrade base` estén verificados desde el
arranque. La FASE 2 añade las primeras tablas reales (`platform_users`,
`merchants`, `merchant_users`, `audit_events`).

Revisión ID: 0001_baseline
Creada: 2026-10-12
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
