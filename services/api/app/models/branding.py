"""Branding de tarjeta del comercio (§11.15, §11.16, decisión #8).

Cada comercio personaliza su tarjeta: colores, icono de sellos, pie de
tarjeta y logotipo. El branding es **presentación**: nunca cambia saldos,
reglas ni estados (la fuente de verdad sigue siendo el ledger, §6.1).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class Asset(Base):
    """Recurso gráfico subido por el comercio (§11.16).

    El contenido se guarda en la base de datos (≤512 KiB validados): evita
    volúmenes de Docker y sirve la imagen con el mismo control de acceso del
    resto de la API. `mime_type` sale de los **magic bytes**, nunca del nombre
    de archivo ni de la extensión (§16.5).
    """

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), default="logo")
    mime_type: Mapped[str] = mapped_column(String(40))
    file_size: Mapped[int] = mapped_column()
    #: Contenido del fichero validado. Nada servido con scripts (§16.5).
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MerchantBranding(Base):
    """Branding de tarjeta por comercio (§11.15): uno a uno con el comercio."""

    __tablename__ = "merchant_branding"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("merchants.id", ondelete="CASCADE"), unique=True, index=True
    )
    #: Colores en hexadecimal `#RRGGBB` validados en el servicio.
    primary_color: Mapped[str] = mapped_column(String(7), default="#5b48d6")
    accent_color: Mapped[str] = mapped_column(String(7), default="#f7bd4b")
    #: Icono del sello: cup | heart | star | leaf | spark (catálogo cerrado).
    stamp_icon: Mapped[str] = mapped_column(String(10), default="cup")
    #: Pie de tarjeta (texto plano, máx. 80): condiciones breves o un saludo.
    footer_text: Mapped[str | None] = mapped_column(String(80), nullable=True)
    logo_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
