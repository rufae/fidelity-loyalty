"""Branding de tarjeta del comercio (decisión de compra #8, §11.15).

Creación perezosa (primera lectura crea la fila por defecto) y validación de
todas las entradas: colores `#RRGGBB`, icono del catálogo cerrado, pie con
límite y logotipo validado por **magic bytes** con tope de 512 KiB (§16.5).
Nada de esto toca la lógica de fidelización: es presentación (§6.1).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DomainError
from app.models.branding import Asset, MerchantBranding

LOGO_MAX_BYTES = 512 * 1024

STAMP_ICONS = ("cup", "heart", "star", "leaf", "spark")


def get_or_create(session: Session, merchant_id: uuid.UUID) -> MerchantBranding:
    """Branding del comercio; la primera vez crea el de por defecto."""
    branding = session.scalar(
        select(MerchantBranding).where(MerchantBranding.merchant_id == merchant_id)
    )
    if branding is None:
        branding = MerchantBranding(merchant_id=merchant_id)
        session.add(branding)
        session.flush()
    return branding


def _validate_hex(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 7 or not normalized.startswith("#"):
        raise DomainError(422, "invalid_color", f"Color {field} no válido")
    hexpart = normalized[1:]
    if any(char not in "0123456789abcdef" for char in hexpart):
        raise DomainError(422, "invalid_color", f"Color {field} no válido")
    return normalized


def _detect_mime(data: bytes) -> str | None:
    """MIME real por magic bytes: solo aceptamos PNG y JPEG (§16.5)."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return None


def save_logo(
    session: Session, merchant_id: uuid.UUID, branding: MerchantBranding, data: bytes
) -> Asset:
    """Valida y guarda el logotipo; sustituye al anterior sin huérfanos."""
    if len(data) == 0:
        raise DomainError(422, "invalid_logo", "El archivo está vacío")
    if len(data) > LOGO_MAX_BYTES:
        raise DomainError(413, "logo_too_large", "El logotipo supera los 512 KB")
    mime = _detect_mime(data)
    if mime is None:
        raise DomainError(415, "invalid_logo", "Solo se aceptan PNG o JPG")

    # El anterior sale de circulación al reasignar; se borra explícito para
    # no acumular bytes muertos en la base de datos.
    if branding.logo_asset_id is not None:
        old = session.get(Asset, branding.logo_asset_id)
        if old is not None:
            session.delete(old)
    asset = Asset(
        merchant_id=merchant_id,
        asset_type="logo",
        mime_type=mime,
        file_size=len(data),
        data=data,
    )
    session.add(asset)
    session.flush()
    branding.logo_asset_id = asset.id
    return asset


def update(
    session: Session,
    merchant_id: uuid.UUID,
    *,
    primary_color: str | None = None,
    accent_color: str | None = None,
    stamp_icon: str | None = None,
    footer_text: str | None = None,
    logo_data: bytes | None = None,
    remove_logo: bool = False,
) -> MerchantBranding:
    """Aplica cambios de diseño validados; todo junto en una sola llamada."""
    branding = get_or_create(session, merchant_id)
    if primary_color is not None:
        branding.primary_color = _validate_hex(primary_color, "principal")
    if accent_color is not None:
        branding.accent_color = _validate_hex(accent_color, "de acento")
    if stamp_icon is not None:
        if stamp_icon not in STAMP_ICONS:
            raise DomainError(422, "invalid_stamp_icon", "Icono no disponible")
        branding.stamp_icon = stamp_icon
    if footer_text is not None:
        footer = footer_text.strip()
        if len(footer) > 80:
            raise DomainError(422, "invalid_footer", "El pie no puede pasar de 80 caracteres")
        branding.footer_text = footer or None
    if logo_data is not None:
        save_logo(session, merchant_id, branding, logo_data)
    if remove_logo and branding.logo_asset_id is not None:
        old = session.get(Asset, branding.logo_asset_id)
        branding.logo_asset_id = None
        if old is not None:
            session.delete(old)
    session.flush()
    return branding


def out_payload(session: Session, branding: MerchantBranding) -> dict[str, object]:
    """Respuesta del branding; la URL del logo es una ruta pública opaca."""
    return {
        "primary_color": branding.primary_color,
        "accent_color": branding.accent_color,
        "stamp_icon": branding.stamp_icon,
        "footer_text": branding.footer_text,
        "logo_url": f"/api/v1/public/assets/{branding.logo_asset_id}"
        if branding.logo_asset_id is not None
        else None,
    }
