"""Programas de fidelización y recompensas (AGENTS.md §7, §11.5, §11.6).

Dos tipos operativos (§7.1, mejora de compra #9):

- `stamps`: sellos enteros por visita (el flujo original).
- `points`: puntos por importe de la venta. El importe lo teclea el
  personal en el mostrador (MVP sin TPV, §7.6) y **el backend** calcula
  los puntos con `points_per_euro` en aritmética Decimal: nunca flotantes
  ni cantidades enviadas por el navegador (§7.6, §11.19).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class ProgramStatus:
    """Estados de un programa (§7.2)."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ProgramType:
    STAMPS = "stamps"
    POINTS = "points"


class LoyaltyProgram(Base):
    __tablename__ = "loyalty_programs"
    __table_args__ = (UniqueConstraint("merchant_id", "slug", name="uq_program_merchant_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(70))
    program_type: Mapped[str] = mapped_column(String(20), default=ProgramType.STAMPS)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default=ProgramStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Caducidad opcional de sellos (decisión de compra #6, §7.7): días
    #: que tarda cada lote de sellos en vencer. `None` = sin caducidad,
    #: que sigue siendo el comportamiento por defecto. Solo afecta a los
    #: `earn` futuros: los lotes ya emitidos conservan su fecha.
    stamps_expire_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Regla del modo `points` (§7.6): puntos enteros por euro gastado.
    #: `None` = sin regla (obligatoria antes de publicar un programa de
    #: puntos). El redondeo es siempre hacia abajo, en el backend.
    points_per_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def is_active(self) -> bool:
        return self.status == ProgramStatus.ACTIVE


class ProgramReward(Base):
    __tablename__ = "program_rewards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("loyalty_programs.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stamps_required: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active"
