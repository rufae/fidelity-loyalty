"""Endpoints de diseño de tarjeta (decisión de compra #8, §13.3).

- Del comercio (owner/admin): leer y actualizar el diseño, subir o quitar el
  logotipo.
- Público: servir el logotipo por UUID opaco; la tarjeta web del cliente
  consume el diseño a través del payload público de la membresía.

La subida del logo es `POST` con el fichero en el cuerpo (`octet-stream`):
no hay multipart y el MIME se decide por **magic bytes**, nunca por la
extensión (§16.5). Nada de esto toca saldos ni reglas: es presentación.
"""

import uuid
from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.deps import DbSession
from app.api.merchants import MerchantAdminDep
from app.api.public import check_public_read_rate
from app.domain.errors import DomainError
from app.models.branding import Asset
from app.services import branding as branding_service
from app.services.audit import record_audit

router = APIRouter(tags=["diseño"])

LOGO_CACHE_SECONDS = 300


class BrandingIn(BaseModel):
    """Cambios de diseño: todo opcional, se aplica lo que llegue."""

    primary_color: str | None = None
    accent_color: str | None = None
    stamp_icon: str | None = None
    footer_text: str | None = None
    remove_logo: bool = False


@router.get("/merchants/{merchant_id}/branding")
def get_branding(
    merchant_id: uuid.UUID,
    session: DbSession,
    _: MerchantAdminDep,
) -> Mapping[str, object]:
    branding = branding_service.get_or_create(session, merchant_id)
    return branding_service.out_payload(session, branding)


@router.put("/merchants/{merchant_id}/branding")
def update_branding(
    merchant_id: uuid.UUID,
    data: BrandingIn,
    session: DbSession,
    context: MerchantAdminDep,
) -> Mapping[str, object]:
    branding = branding_service.update(
        session,
        merchant_id,
        primary_color=data.primary_color,
        accent_color=data.accent_color,
        stamp_icon=data.stamp_icon,
        footer_text=data.footer_text,
        remove_logo=data.remove_logo,
    )
    record_audit(
        session,
        action="branding.updated",
        entity_type="merchant_branding",
        entity_id=str(merchant_id),
        actor_id=context.user.id,
        merchant_id=merchant_id,
        metadata={"fields": "colors,icon,footer,logo"},
    )
    session.commit()
    return branding_service.out_payload(session, branding)


@router.post("/merchants/{merchant_id}/branding/logo")
async def upload_logo(
    merchant_id: uuid.UUID,
    request: Request,
    session: DbSession,
    context: MerchantAdminDep,
) -> Mapping[str, object]:
    """Sube el logotipo: cuerpo binario, MIME real por magic bytes (§16.5)."""
    data = await request.body()
    branding = branding_service.update(session, merchant_id, logo_data=data)
    record_audit(
        session,
        action="branding.logo_uploaded",
        entity_type="merchant_branding",
        entity_id=str(merchant_id),
        actor_id=context.user.id,
        merchant_id=merchant_id,
    )
    session.commit()
    return branding_service.out_payload(session, branding)


@router.delete("/merchants/{merchant_id}/branding/logo")
def delete_logo(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantAdminDep,
) -> Mapping[str, object]:
    branding = branding_service.update(session, merchant_id, remove_logo=True)
    record_audit(
        session,
        action="branding.logo_removed",
        entity_type="merchant_branding",
        entity_id=str(merchant_id),
        actor_id=context.user.id,
        merchant_id=merchant_id,
    )
    session.commit()
    return branding_service.out_payload(session, branding)


@router.get("/public/assets/{asset_id}")
def get_asset(
    asset_id: uuid.UUID,
    session: DbSession,
    _: Annotated[None, Depends(check_public_read_rate)],
) -> Response:
    """Sirve el recurso gráfico por UUID opaco (sin datos personales, §9.3).

    El UUID no adivina nada y no concede permisos: solo muestra una imagen ya
    validada. Cabeceras de caché y sin sniffing (§16.7).
    """
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise DomainError(404, "asset_not_found", "Recurso no encontrado")
    return Response(
        content=asset.data,
        media_type=asset.mime_type,
        headers={
            "Cache-Control": f"public, max-age={LOGO_CACHE_SECONDS}",
            "X-Content-Type-Options": "nosniff",
        },
    )
