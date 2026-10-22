"""Etiquetas NFC/QR y destinos de reseñas (AGENTS.md §5, §11.12-§11.14, §4).

Dos recorridos **independientes** que comparten infraestructura pero nunca
lógica (§1.2, §5.1):

- `loyalty_signup`: abre la página pública de alta de un programa.
- `google_review`: abre el destino oficial de reseñas **verificado** del
  comercio, de forma neutral y sin incentivos (§4.2).

Ninguna columna vincula una recompensa o un sello con una reseña: esa
combinación no puede modelarse, no solo está prohibida (§4.2).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class TagType:
    LOYALTY_SIGNUP = "loyalty_signup"
    GOOGLE_REVIEW = "google_review"
    #: Atajo de mostrador: el personal la toca con su móvil para abrir las
    #: operaciones con el programa ya elegido. Nunca suma sellos por sí sola.
    COUNTER = "counter"
    MEMBER_CARD_ACCESS = "member_card_access"


class TagStatus:
    ACTIVE = "active"
    DISABLED = "disabled"


class NfcTag(Base):
    __tablename__ = "nfc_tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    tag_type: Mapped[str] = mapped_column(String(30))
    #: Ruta corta pública (`/go/{public_slug}`): aleatoria, no predecible y
    #: **sin datos personales** (§5.2).
    public_slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    #: Para `loyalty_signup`: programa de destino.
    destination_program_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    #: Para `google_review`: destino verificado asociado.
    review_destination_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TagStatus.ACTIVE)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewDestination(Base):
    """Destino oficial de reseñas del comercio (§4.1, §11.13)."""

    __tablename__ = "review_destinations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), default="google")
    review_url: Mapped[str] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class RedirectEvent(Base):
    """Métrica mínima de clics/escaneos (§4.4, §11.14). Sin IP ni fingerprint."""

    __tablename__ = "redirect_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    event_type: Mapped[str] = mapped_column(String(30), default="link_click")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
