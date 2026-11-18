"""Identidad: usuarios, sesiones y pertenencia a comercios (§8, §11).

**Decisión (documentada en docs/ADR/0003-identidad-y-autenticación.md):**
existe **una sola tabla de identidad** (`users`) en lugar de `platform_users`
y `merchant_users` como entidades de credencial separadas (§11.1/§11.4). Un
mismo email no debe tener dos contraseñas distintas ni dos recuperaciones de
contraseña: la pertenencia a comercios se modela con `merchant_users`, que es
exactamente la relación que el §11.4 describe.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.roles import MerchantRole, PlatformRole, UserStatus, role_rank


def utcnow() -> datetime:
    """Siempre UTC en almacenamiento (§11.19); la interfaz convierte a la zona del comercio."""
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    platform_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_platform_admin(self) -> bool:
        return self.platform_role in {r.value for r in PlatformRole}

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value


class MerchantUser(Base):
    """Relación usuario ↔ comercio con su rol (§11.4)."""

    __tablename__ = "merchant_users"
    __table_args__ = (UniqueConstraint("user_id", "merchant_id", name="uq_merchant_user"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value

    def allows(self, minimum: MerchantRole) -> bool:
        """¿Cumple este rol como mínimo el rango pedido?"""
        try:
            return role_rank(MerchantRole(self.role)) >= role_rank(minimum)
        except ValueError:
            return False


class UserSession(Base):
    """Sesiones en servidor: permite invalidar concretamente una sesión (§8.3)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires > datetime.now(UTC)


class PasswordResetToken(Base):
    """Solicitud de recuperación de contraseña de personal (§8.3).

    Un solo uso, caduca en 30 minutos y se guarda **hasheado** (igual que los
    tokens de acceso a tarjeta): filtrar la tabla no filtra los enlaces.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
