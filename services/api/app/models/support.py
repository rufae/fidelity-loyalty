"""Soporte B2B: conversaciones del comercio con la plataforma (Plan.md §8).

Todo el módulo es **privado y autenticado**: no hay formulario público. Cada
conversación pertenece a un comercio y el teléfono de una solicitud de llamada
se guarda **cifrado** (`app/core/crypto.py`), nunca en claro.

El outbox `support_notifications` nace en la misma transacción que el mensaje:
un fallo de correo o push jamás borra ni retrasa la conversación, que queda en
el buzón del panel.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class SupportThreadStatus:
    OPEN = "open"
    WAITING_PLATFORM = "waiting_platform"
    WAITING_MERCHANT = "waiting_merchant"
    RESOLVED = "resolved"
    CLOSED = "closed"

    ALL = {OPEN, WAITING_PLATFORM, WAITING_MERCHANT, RESOLVED, CLOSED}
    OPEN_STATUSES = {OPEN, WAITING_PLATFORM, WAITING_MERCHANT}


class SupportCategory:
    TECHNICAL = "technical"
    BILLING = "billing"
    PROGRAM = "program"
    NFC = "nfc"
    WALLET = "wallet"
    OTHER = "other"

    ALL = {TECHNICAL, BILLING, PROGRAM, NFC, WALLET, OTHER}


class SupportPriority:
    NORMAL = "normal"
    HIGH = "high"

    ALL = {NORMAL, HIGH}


class SupportContactPreference:
    IN_APP = "in_app"
    EMAIL = "email"
    PHONE = "phone"

    ALL = {IN_APP, EMAIL, PHONE}


class SupportAuthorType:
    MERCHANT = "merchant"
    PLATFORM = "platform"


class SupportCallbackStatus:
    REQUESTED = "requested"
    CALLED = "called"
    CANCELLED = "cancelled"

    ALL = {REQUESTED, CALLED, CANCELLED}


class SupportNotificationChannel:
    EMAIL_PLATFORM = "email_platform"
    EMAIL_MERCHANT = "email_merchant"
    NTFY = "ntfy"
    TELEGRAM = "telegram"

    ALL = {EMAIL_PLATFORM, EMAIL_MERCHANT, NTFY, TELEGRAM}


class SupportNotificationStatus:
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ALL = {QUEUED, RUNNING, SUCCEEDED, RETRYING, FAILED, CANCELLED}
    DUE = {QUEUED, RETRYING}


class SupportThread(Base):
    __tablename__ = "support_threads"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key", name="uq_support_thread_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    subject: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(20), default=SupportCategory.OTHER)
    status: Mapped[str] = mapped_column(
        String(20), default=SupportThreadStatus.WAITING_PLATFORM, index=True
    )
    priority: Mapped[str] = mapped_column(String(20), default=SupportPriority.NORMAL)
    preferred_contact: Mapped[str] = mapped_column(
        String(20), default=SupportContactPreference.IN_APP
    )
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"
    __table_args__ = (
        UniqueConstraint("thread_id", "idempotency_key", name="uq_support_message_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_threads.id", ondelete="CASCADE"), index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    author_type: Mapped[str] = mapped_column(String(20))
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    body: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    read_by_merchant_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    read_by_platform_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupportCallbackRequest(Base):
    """Solicitud de llamada privada: la app solo guarda el pedido (Plan.md §7)."""

    __tablename__ = "support_callback_requests"
    __table_args__ = (
        UniqueConstraint("thread_id", "idempotency_key", name="uq_support_callback_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_threads.id", ondelete="CASCADE"), index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), index=True
    )
    #: Teléfono cifrado (§12.2 de Plan.md). Nunca sale en correos ni push.
    phone_encrypted: Mapped[str] = mapped_column(String(512))
    availability: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SupportCallbackStatus.REQUESTED, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SupportNotification(Base):
    """Outbox de avisos: estado persistido, reintentos y reintento manual (§15)."""

    __tablename__ = "support_notifications"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_support_notification_idem"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("support_threads.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("support_messages.id", ondelete="CASCADE"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(20), default=SupportNotificationStatus.QUEUED, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    manual_retries: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160))
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
