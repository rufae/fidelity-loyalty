"""Servicio de etiquetas y destinos de reseñas (§4, §5, §14).

Reglas aplicadas aquí:
- El destino de reseñas debe estar **verificado** antes de que una etiqueta
  redirija a él (§4.1): sin verificar, `/go/{slug}` responde
  `review_destination_not_verified`.
- La ruta `/go/{slug}` **solo** resuelve al destino guardado: no acepta URLs
  libres ni parámetros de destino (§12.8, sin *open redirect*).
- El redirect ignora cualquier parámetro de la URL: no hay filtros por
  satisfacción ni por historial (§4.2).
"""

import secrets
import uuid
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DomainError, not_found
from app.models.loyalty import LoyaltyProgram
from app.models.nfc import NfcTag, RedirectEvent, ReviewDestination, TagStatus, TagType
from app.models.user import utcnow
from app.schemas.nfc import NfcTagCreate, NfcTagUpdate


def new_public_slug() -> str:
    return secrets.token_hex(8)  # 128 bits: no predecible (§5.2)


#: Hosts de Google permitidos para enlaces de reseñas (§4.1, §16.3). Coincidencia
#: exacta de hostname: `google.com.ejemplo-malicioso.com` o
#: `ejemplo.com/google.com` NO pasan (corrección de la auditoría).
ALLOWED_REVIEW_HOSTS = frozenset(
    {
        "google.com",
        "www.google.com",
        "maps.google.com",
        "maps.app.goo.gl",
        "search.google.com",
        "local.google.com",
        "business.google.com",
        "g.page",
    }
)


def validate_review_url(url: str) -> str:
    """Solo HTTPS y en hosts oficiales de Google (§4.1, §16.3)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_REVIEW_HOSTS:
        raise DomainError(
            422,
            "invalid_review_url",
            "La URL de reseñas debe ser https y apuntar a Google "
            "(google.com, maps.app.goo.gl, g.page…)",
        )
    return url


def get_destination(session: Session, merchant_id: uuid.UUID) -> ReviewDestination | None:
    return session.scalar(
        select(ReviewDestination).where(ReviewDestination.merchant_id == merchant_id)
    )


def upsert_destination(
    session: Session, merchant_id: uuid.UUID, review_url: str
) -> ReviewDestination:
    """Guardar el destino invalida la verificación previa (§4.1)."""
    url = validate_review_url(review_url)
    destination = get_destination(session, merchant_id)
    if destination is None:
        destination = ReviewDestination(merchant_id=merchant_id, review_url=url)
        session.add(destination)
    else:
        if destination.review_url != url:
            destination.verification_status = "unverified"
            destination.verified_at = None
        destination.review_url = url
    session.flush()
    return destination


def verify_destination(session: Session, merchant_id: uuid.UUID) -> ReviewDestination:
    destination = get_destination(session, merchant_id)
    if destination is None:
        raise not_found("Destino de reseñas")
    destination.verification_status = "verified"
    destination.verified_at = utcnow()
    session.flush()
    return destination


def _program_for_tag(
    session: Session, merchant_id: uuid.UUID, program_id: uuid.UUID | None, message: str
) -> LoyaltyProgram:
    """Programa del comercio para una etiqueta; 422 si falta, 404 si no es suyo."""
    if program_id is None:
        raise DomainError(422, "program_required", message)
    program = session.scalar(
        select(LoyaltyProgram).where(
            LoyaltyProgram.id == program_id,
            LoyaltyProgram.merchant_id == merchant_id,
        )
    )
    if program is None:
        raise not_found("Programa")
    return program


def create_tag(session: Session, merchant_id: uuid.UUID, data: NfcTagCreate) -> tuple[NfcTag, str]:
    """Crea la etiqueta y devuelve su URL pública (§5.4, §14.3)."""
    destination_url: str
    if data.tag_type == TagType.LOYALTY_SIGNUP:
        program = _program_for_tag(
            session,
            merchant_id,
            data.program_id,
            "Una etiqueta de alta necesita un programa",
        )
        merchant_slug = _merchant_slug(session, merchant_id)
        tag = NfcTag(
            merchant_id=merchant_id,
            tag_type=TagType.LOYALTY_SIGNUP,
            public_slug=new_public_slug(),
            destination_program_id=program.id,
            label=data.label,
        )
        destination_url = f"/p/{merchant_slug}/{program.slug}"
    elif data.tag_type == TagType.COUNTER:
        # Atajo de mostrador (ADR-0008): abre las operaciones con el programa
        # ya elegido. La etiqueta **nunca** suma sellos por sí sola: solo
        # ahorra al personal un paso. Requiere sesión del comercio.
        program = _program_for_tag(
            session,
            merchant_id,
            data.program_id,
            "Una etiqueta de mostrador necesita un programa",
        )
        tag = NfcTag(
            merchant_id=merchant_id,
            tag_type=TagType.COUNTER,
            public_slug=new_public_slug(),
            destination_program_id=program.id,
            label=data.label,
        )
        destination_url = f"/merchants/{merchant_id}/operations?program={program.id}"
    elif data.tag_type == TagType.MEMBER_CARD_ACCESS:
        tag = NfcTag(
            merchant_id=merchant_id,
            tag_type=TagType.MEMBER_CARD_ACCESS,
            public_slug=new_public_slug(),
            label=data.label,
        )
        destination_url = f"/my-card/{_merchant_slug(session, merchant_id)}"
    else:
        destination = get_destination(session, merchant_id)
        if destination is None:
            raise DomainError(
                422,
                "review_destination_required",
                "Configura primero el enlace oficial de reseñas del comercio",
            )
        tag = NfcTag(
            merchant_id=merchant_id,
            tag_type=TagType.GOOGLE_REVIEW,
            public_slug=new_public_slug(),
            review_destination_id=destination.id,
            label=data.label,
        )
        destination_url = destination.review_url

    session.add(tag)
    session.flush()
    return tag, destination_url


def _merchant_slug(session: Session, merchant_id: uuid.UUID) -> str:
    from app.models.merchant import Merchant

    merchant = session.get(Merchant, merchant_id)
    assert merchant is not None
    return merchant.slug


def tag_public_url(session: Session, tag: NfcTag) -> str:
    if tag.tag_type == TagType.LOYALTY_SIGNUP and tag.destination_program_id is not None:
        program = session.get(LoyaltyProgram, tag.destination_program_id)
        if program is not None:
            return f"/p/{_merchant_slug(session, tag.merchant_id)}/{program.slug}"
    if tag.tag_type == TagType.COUNTER and tag.destination_program_id is not None:
        # Atajo de mostrador: operaciones con el programa preseleccionado.
        return f"/merchants/{tag.merchant_id}/operations?program={tag.destination_program_id}"
    if tag.tag_type == TagType.MEMBER_CARD_ACCESS:
        return f"/my-card/{_merchant_slug(session, tag.merchant_id)}"
    destination = session.get(ReviewDestination, tag.review_destination_id or uuid.uuid4())
    return destination.review_url if destination else ""


def update_tag(session: Session, tag: NfcTag, data: NfcTagUpdate) -> NfcTag:
    if data.label is not None:
        tag.label = data.label
    if data.status is not None:
        tag.status = data.status
    session.flush()
    return tag


def get_tag(session: Session, merchant_id: uuid.UUID, tag_id: uuid.UUID) -> NfcTag:
    tag = session.scalar(
        select(NfcTag).where(NfcTag.id == tag_id, NfcTag.merchant_id == merchant_id)
    )
    if tag is None:
        raise not_found("Etiqueta")
    return tag


def list_tags(session: Session, merchant_id: uuid.UUID) -> list[NfcTag]:
    rows = session.scalars(select(NfcTag).where(NfcTag.merchant_id == merchant_id)).all()
    return sorted(rows, key=lambda t: t.created_at, reverse=True)


def record_click(session: Session, tag: NfcTag) -> RedirectEvent:
    """Métrica mínima: sin IP, sin user-agent, sin identidad del cliente (§4.4)."""
    event = RedirectEvent(merchant_id=tag.merchant_id, tag_id=tag.id)
    session.add(event)
    session.flush()
    return event


def resolve_redirect(session: Session, public_slug: str) -> tuple[NfcTag, str]:
    """Resuelve `/go/{slug}` contra **solo** el destino guardado (§12.8)."""
    tag = session.scalar(select(NfcTag).where(NfcTag.public_slug == public_slug))
    if tag is None:
        raise DomainError(404, "tag_not_found", "Etiqueta no encontrada")
    if tag.status != TagStatus.ACTIVE:
        raise DomainError(410, "tag_disabled", "Esta etiqueta está desactivada")

    if tag.tag_type == TagType.LOYALTY_SIGNUP:
        # Métrica mínima del clic (corrige: antes no se registraba ningún
        # clic de alta y la estadística quedaba siempre a cero).
        record_click(session, tag)
        return tag, tag_public_url(session, tag)

    if tag.tag_type == TagType.COUNTER:
        # Uso del atajo por el personal: se cuenta como clic de mostrador.
        record_click(session, tag)
        return tag, tag_public_url(session, tag)

    if tag.tag_type == TagType.MEMBER_CARD_ACCESS:
        record_click(session, tag)
        return tag, tag_public_url(session, tag)

    destination = (
        session.get(ReviewDestination, tag.review_destination_id)
        if tag.review_destination_id
        else None
    )
    if destination is None:
        raise not_found("Destino de reseñas")
    if destination.verification_status != "verified":
        # §4.1: nunca se afirma que un enlace es oficial sin verificarlo.
        raise DomainError(
            404,
            "review_destination_not_verified",
            "El enlace de reseñas aún no está verificado",
        )
    record_click(session, tag)
    return tag, destination.review_url


def stats(session: Session, merchant_id: uuid.UUID) -> dict[str, int]:
    tags = list_tags(session, merchant_id)
    events = session.scalars(
        select(RedirectEvent).where(RedirectEvent.merchant_id == merchant_id)
    ).all()
    by_tag = {t.id: t.tag_type for t in tags}
    review_clicks = sum(1 for e in events if by_tag.get(e.tag_id) == TagType.GOOGLE_REVIEW)
    signup_clicks = sum(1 for e in events if by_tag.get(e.tag_id) == TagType.LOYALTY_SIGNUP)
    counter_clicks = sum(1 for e in events if by_tag.get(e.tag_id) == TagType.COUNTER)
    card_access_clicks = sum(
        1 for e in events if by_tag.get(e.tag_id) == TagType.MEMBER_CARD_ACCESS
    )
    return {
        "loyalty_signup_clicks": signup_clicks,
        # Nombre exacto (§4.4, §12.9): es un clic, no una reseña publicada.
        "review_link_clicks": review_clicks,
        # Usos del atajo de mostrador por el personal (ADR-0008).
        "counter_clicks": counter_clicks,
        "member_card_access_clicks": card_access_clicks,
        "total_clicks": len(events),
        "tags_active": sum(1 for t in tags if t.status == TagStatus.ACTIVE),
    }
