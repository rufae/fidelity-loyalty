"""Miembros (clientes del comercio) y membresías (§11.7, §11.8).

Decisión de privacidad (§11.7): el cliente se aísla **por comercio**; no existe
identidad global entre comercios. Los datos son mínimos: el alta puede ser solo
con un identificador opaco y, si se recoge email, se hace para la gestión de
la membresía (§9.3).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("merchant_id", "email", name="uq_member_email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    #: Obligatorio en altas nuevas (ADR-0006); nullable por compatibilidad con
    #: registros históricos creados con el flujo de datos mínimos.
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    #: Consentimientos registrados (ADR-0006, §9.4): marketing es opcional y
    #: nunca se presupone; el aviso de privacidad guarda la versión aceptada.
    privacy_notice_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marketing_consent: Mapped[int] = mapped_column(Integer, default=0)
    marketing_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Membership(Base):
    """Relación cliente ↔ programa, con token público opaco (§5.2, §6.3)."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("member_id", "program_id", name="uq_membership_program"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    program_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    #: Token opaco público (256 bits). No es una credencial de administración
    #: ni da acceso a datos privados del comercio (§5.2).
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    #: De dónde nace la tarjeta (ADR-0006 revisado): "public" (la verificación
    #: de email es requisito) o "counter" (entrega presencial: el email se
    #: registra sin verificar y **no** bloquea la tarjeta).
    origin: Mapped[str] = mapped_column(String(20), default="public", server_default="public")
    #: Ciclo de vida (ADR-0005): motivo/fecha del último cambio de estado y
    #: trazas de supresión de datos. `anonymized` conserva el ledger asociado.
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Sellos materializados para lectura rápida; el **ledger** es la fuente
    #: de verdad (§7.3) y debe poder reconciliarse con él.
    stamps: Mapped[int] = mapped_column(Integer, default=0)
    #: Control optimista de concurrencia en operaciones de saldo (§16.4).
    version: Mapped[int] = mapped_column(Integer, default=0)
    terms_version_accepted: Mapped[int] = mapped_column(Integer, default=1)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
