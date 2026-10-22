"""Comercios (clientes de la plataforma) — §11.2, §11.3."""

import re
import unicodedata
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.roles import MerchantStatus
from app.models.user import utcnow


def slugify(value: str) -> str:
    """Slug legible y estable para URLs públicas (§5.2, §12.5).

    No es un control de acceso (§11.2): el acceso se decide por sesión y rol,
    nunca por adivinar el slug.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:60] or "comercio"


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(70), unique=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=MerchantStatus.ACTIVE.value)
    timezone: Mapped[str] = mapped_column(String(60), default="Europe/Madrid")
    country_code: Mapped[str] = mapped_column(String(2), default="ES")
    default_locale: Mapped[str] = mapped_column(String(10), default="es")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    @property
    def is_active(self) -> bool:
        return self.status == MerchantStatus.ACTIVE.value
