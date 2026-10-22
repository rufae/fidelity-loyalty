"""API de etiquetas NFC/QR y destino de reseñas (§12.8).

Todo exige administración del comercio (`owner`/`admin`). El redirect público
vive en `app/api/go.py` (§12.8).
"""

import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import DbSession, merchant_access
from app.core.config import Settings, get_settings
from app.core.urls import absolute_url, resolve_public_base
from app.domain.roles import MERCHANT_ADMIN_ROLES
from app.models.nfc import NfcTag
from app.schemas.nfc import (
    NfcStatsOut,
    NfcTagCreate,
    NfcTagOut,
    NfcTagUpdate,
    ReviewDestinationIn,
    ReviewDestinationOut,
)
from app.services import nfc as nfc_service
from app.services.audit import record_audit

router = APIRouter(prefix="/merchants/{merchant_id}", tags=["nfc"])
admin = merchant_access(MERCHANT_ADMIN_ROLES)
AdminDep = Annotated[object, Depends(admin)]


def _tag_out(session: Session, tag: NfcTag, base: str) -> NfcTagOut:
    slug = tag.public_slug
    return NfcTagOut(
        id=tag.id,
        tag_type=tag.tag_type,
        public_slug=slug,
        status=tag.status,
        label=tag.label,
        destination_url=nfc_service.tag_public_url(session, tag),
        # URL absoluta que se escribe en la etiqueta NFC y se imprime en el QR:
        # una ruta relativa no abre nada al escanearla con un móvil (§14.1).
        short_url=absolute_url(f"/go/{slug}", base),
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )


@router.get("/review-destination", response_model=ReviewDestinationOut | None)
def get_destination(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> ReviewDestinationOut | None:
    destination = nfc_service.get_destination(session, merchant_id)
    return ReviewDestinationOut.model_validate(destination) if destination else None


@router.put("/review-destination", response_model=ReviewDestinationOut)
def put_destination(
    merchant_id: uuid.UUID,
    data: ReviewDestinationIn,
    session: DbSession,
    context: AdminDep,
) -> ReviewDestinationOut:
    """Guarda el enlace oficial. Al cambiarlo se pierde la verificación (§4.1)."""
    destination = nfc_service.upsert_destination(session, merchant_id, data.review_url)
    record_audit(
        session,
        action="review_destination.updated",
        entity_type="review_destination",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(destination.id),
    )
    session.commit()
    return ReviewDestinationOut.model_validate(destination)


@router.post("/review-destination/verify", response_model=ReviewDestinationOut)
def verify_destination(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,
) -> ReviewDestinationOut:
    """El comercio confirma manualmente que el enlace abre su página oficial."""
    destination = nfc_service.verify_destination(session, merchant_id)
    record_audit(
        session,
        action="review_destination.verified",
        entity_type="review_destination",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(destination.id),
    )
    session.commit()
    return ReviewDestinationOut.model_validate(destination)


@router.get("/nfc-tags", response_model=list[NfcTagOut])
def list_tags(
    merchant_id: uuid.UUID,
    request: Request,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[NfcTagOut]:
    base = resolve_public_base(request, settings)
    return [_tag_out(session, t, base) for t in nfc_service.list_tags(session, merchant_id)]


@router.post("/nfc-tags", response_model=NfcTagOut, status_code=201)
def create_tag(
    merchant_id: uuid.UUID,
    data: NfcTagCreate,
    request: Request,
    session: DbSession,
    context: AdminDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> NfcTagOut:
    tag, _url = nfc_service.create_tag(session, merchant_id, data)
    record_audit(
        session,
        action="nfc_tag.created",
        entity_type="nfc_tag",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(tag.id),
        metadata={"fields": [data.tag_type]},
    )
    session.commit()
    return _tag_out(session, tag, resolve_public_base(request, settings))


@router.patch("/nfc-tags/{tag_id}", response_model=NfcTagOut)
def update_tag(
    merchant_id: uuid.UUID,
    tag_id: uuid.UUID,
    data: NfcTagUpdate,
    request: Request,
    session: DbSession,
    context: AdminDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> NfcTagOut:
    tag = nfc_service.get_tag(session, merchant_id, tag_id)
    tag = nfc_service.update_tag(session, tag, data)
    record_audit(
        session,
        action="nfc_tag.updated",
        entity_type="nfc_tag",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(tag.id),
        metadata={"new_status": tag.status},
    )
    session.commit()
    return _tag_out(session, tag, resolve_public_base(request, settings))


@router.get("/nfc-tags/{tag_id}/qr")
def tag_qr(
    merchant_id: uuid.UUID,
    tag_id: uuid.UUID,
    request: Request,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """QR (SVG) con la URL corta **absoluta** de la etiqueta (§5.2, §14.1).

    El contenido debe ser una URL completa: si el QR llevara `/go/{slug}` el
    móvil mostraría el texto al escanearlo en lugar de abrir la etiqueta. El
    contenido exacto se devuelve además en `X-QR-Content` para poder comprobar
    que lo impreso y lo mostrado en pantalla coinciden.
    """
    tag = nfc_service.get_tag(session, merchant_id, tag_id)
    import segno

    base = resolve_public_base(request, settings)
    content = absolute_url(f"/go/{tag.public_slug}", base)
    qr = segno.make(content, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=8, border=2)
    return Response(
        content=buffer.getvalue(),
        media_type="image/svg+xml",
        headers={"X-QR-Content": content},
    )


@router.get("/nfc/stats", response_model=NfcStatsOut)
def stats(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> NfcStatsOut:
    """Clics por tipo de etiqueta. Nunca «reseñas recibidas» (§4.4, §12.9)."""
    return NfcStatsOut(**nfc_service.stats(session, merchant_id))
