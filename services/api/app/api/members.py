"""API de miembros y membresías (§12.5).

Pública: alta (`/public/programs/.../enroll`) y tarjeta (`/public/memberships/{token}`).
Del comercio: listados, restringidos a `owner`/`admin` (§8.2).
"""

import hashlib
import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import DbSession, merchant_access
from app.api.merchants import MerchantAdminDep
from app.api.public import (
    card_access_limiter,
    check_public_rate,
    check_public_read_rate,
    enroll_limiter,
)
from app.core.config import Settings, get_settings
from app.core.urls import absolute_url, resolve_public_base
from app.domain.errors import DomainError
from app.domain.roles import MERCHANT_OPERATOR_ROLES
from app.integrations.wallet import get_wallet_provider
from app.integrations.wallet.apple import AppleWalletProvider
from app.integrations.wallet.google import GoogleWalletProvider
from app.integrations.wallet.pkpass import PassBuildError
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.user import utcnow
from app.schemas.members import (
    CardAccessOut,
    CardAccessRequest,
    EmailActionIn,
    EnrollRequest,
    EnrollResponse,
    MemberOut,
    MembershipOut,
    PublicMembershipOut,
)
from app.services import card_access as card_access_service
from app.services import email as email_service
from app.services import lifecycle
from app.services import members as members_service
from app.services import wallet as wallet_service
from app.services.audit import record_audit

router = APIRouter(tags=["miembros"])

merchant_operator = merchant_access(MERCHANT_OPERATOR_ROLES)
OperatorDep = Annotated[object, Depends(merchant_operator)]


@router.post(
    "/public/programs/{merchant_slug}/{program_slug}/enroll",
    response_model=EnrollResponse,
    status_code=201,
)
def enroll(
    merchant_slug: str,
    program_slug: str,
    data: EnrollRequest,
    request: Request,
    session: DbSession,
    _: Annotated[None, Depends(check_public_rate)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EnrollResponse:
    """Alta de un cliente en el programa (endpoint público, con límite por IP)."""
    # Anti-enumeración (§8.2): además del límite por IP, el mismo correo sobre
    # el mismo programa no puede repetirse en masa.
    if not enroll_limiter.allow(f"{data.email.strip().lower()}|{merchant_slug}|{program_slug}", 0):
        from fastapi import HTTPException

        raise HTTPException(status_code=429, detail="Demasiadas peticiones")
    email_service.ensure_email_configured(settings)
    membership, merchant, program, created = members_service.enroll(
        session,
        merchant_slug,
        program_slug,
        email=str(data.email),
        display_name=data.display_name,
        accepted_terms_version=data.accepted_terms_version,
        privacy_notice_version=data.privacy_notice_version,
        marketing_consent=data.marketing_consent,
    )
    member = session.get(Member, membership.member_id)
    if member is None or member.email is None:
        raise DomainError(404, "membership_not_found", "No se pudo preparar el alta.")
    verified = member.email_verified_at is not None
    purpose = "card_access" if verified else "email_verification"
    raw_token = card_access_service.issue_email_token(
        session, member, merchant.id, purpose, membership.id if not verified else None
    )
    # Auditoría SOLO cuando se crea una membresía nueva: una solicitud repetida
    # (reintento del cliente, doble toque en el botón) reenvía el enlace pero no
    # duplica el evento, y un alta en un segundo programa sí queda registrada.
    if created:
        record_audit(
            session,
            action="member.enrolled",
            entity_type="membership",
            actor_type="member",
            merchant_id=merchant.id,
            entity_id=str(membership.id),
            metadata={"fields": ["email", "display_name", "consents"]},
        )
    session.commit()
    base_url = resolve_public_base(request, settings)
    if verified:
        action_url = absolute_url(f"/card/access?token={raw_token}&m={merchant.slug}", base_url)
        email_service.send_email(
            settings,
            member.email,
            f"Tu tarjeta de {merchant.name}",
            (
                f"Ya puedes abrir tu tarjeta del programa {program.name}. "
                "El enlace es personal y de un solo uso; al usarlo quedarás "
                "identificado en ese dispositivo durante 30 días."
            ),
            action_url,
            cta_label="Abrir mi tarjeta",
            merchant_name=merchant.name,
        )
        return EnrollResponse(message="Te hemos enviado un enlace seguro para abrir tu tarjeta.")
    action_url = absolute_url(f"/card/verify?token={raw_token}&m={merchant.slug}", base_url)
    email_service.send_email(
        settings,
        member.email,
        "Confirma tu correo para activar tu tarjeta",
        f"Confirma que controlas este correo para completar el alta en {merchant.name}.",
        action_url,
        cta_label="Confirmar mi correo",
        merchant_name=merchant.name,
    )
    return EnrollResponse(message="Revisa tu correo para confirmar el alta y activar tu tarjeta.")


@router.post("/public/email/verify", status_code=200)
def verify_member_email(
    data: EmailActionIn,
    response: Response,
    session: DbSession,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(check_public_rate)],
) -> dict[str, str]:
    """Consume una sola vez el enlace de verificación y abre la sesión del cliente."""
    # Comprueba el transporte ANTES de consumir el enlace: si el SMTP fallara,
    # el token no queda gastado sin que el cliente llegue a verlo.
    email_service.ensure_email_configured(settings)
    action = card_access_service.consume_email_token(session, data.token, "email_verification")
    member = session.get(Member, action.member_id)
    membership = session.get(Membership, action.membership_id) if action.membership_id else None
    if member is None or membership is None or member.email is None:
        raise DomainError(400, "invalid_or_expired_link", "El enlace no es válido o ha caducado.")
    member.email_verified_at = member.email_verified_at or utcnow()
    card_session = card_access_service.create_card_session(session, member.id, action.merchant_id)
    access_token = card_access_service.issue_email_token(
        session, member, action.merchant_id, "card_access"
    )
    merchant = session.get(Merchant, action.merchant_id)
    if merchant is None:
        raise DomainError(400, "invalid_or_expired_link", "El enlace no es válido o ha caducado.")
    session.commit()
    email_service.send_email(
        settings,
        member.email,
        f"Tu tarjeta de {merchant.name}",
        (
            "Con este enlace abres tu tarjeta. Es de un solo uso; en el "
            "dispositivo desde el que lo abras quedarás identificado 30 días."
        ),
        absolute_url(
            f"/card/access?token={access_token}&m={merchant.slug}",
            resolve_public_base(request, settings),
        ),
        cta_label="Abrir mi tarjeta",
        merchant_name=merchant.name,
    )
    _set_card_cookie(response, card_session, settings)
    return {"merchant_slug": merchant.slug}


@router.post("/public/card-access/request", status_code=202)
def request_card_access(
    merchant_slug: str,
    data: CardAccessRequest,
    request: Request,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(check_public_rate)],
) -> dict[str, str]:
    """Pide un enlace temporal sin revelar si el correo está registrado."""
    from fastapi import HTTPException
    from sqlalchemy import select

    key = f"{data.email.strip().lower()}|{merchant_slug}"
    if not card_access_limiter.allow(key, 0):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones. Inténtalo más tarde.")
    email_service.ensure_email_configured(settings)
    merchant = session.scalar(select(Merchant).where(Merchant.slug == merchant_slug))
    member = (
        session.scalar(
            select(Member)
            .join(Membership, Membership.member_id == Member.id)
            .where(
                Member.merchant_id == merchant.id,
                Member.email == str(data.email).strip().lower(),
                Member.status == "active",
                Membership.status == "active",
            )
        )
        if merchant is not None
        else None
    )
    if member is not None and merchant is not None:
        verification_needed = member.email_verified_at is None
        membership = (
            session.scalar(
                select(Membership).where(
                    Membership.member_id == member.id,
                    Membership.merchant_id == merchant.id,
                    Membership.status == "active",
                )
            )
            if verification_needed
            else None
        )
        token = card_access_service.issue_email_token(
            session,
            member,
            merchant.id,
            "email_verification" if verification_needed else "card_access",
            membership.id if membership is not None else None,
        )
        session.commit()
        action_path = (
            f"/card/verify?token={token}&m={merchant.slug}"
            if verification_needed
            else f"/card/access?token={token}&m={merchant.slug}"
        )
        email_service.send_email(
            settings,
            member.email or str(data.email),
            (
                f"Confirma tu correo para acceder a {merchant.name}"
                if verification_needed
                else f"Acceso a tus tarjetas de {merchant.name}"
            ),
            (
                "Confirma que controlas este correo. El enlace caduca y solo puede usarse una vez."
                if verification_needed
                else (
                    "Usa este enlace personal para abrir tus tarjetas: es de un "
                    "solo uso y caduca. En el dispositivo desde el que lo abras "
                    "quedarás identificado durante 30 días."
                )
            ),
            absolute_url(action_path, resolve_public_base(request, settings)),
            cta_label="Confirmar mi correo" if verification_needed else "Abrir mis tarjetas",
            merchant_name=merchant.name,
        )
    return {"message": "Si existe una tarjeta asociada, recibirás un enlace seguro por correo."}


@router.post("/public/card-access", status_code=200)
def exchange_card_access(
    data: EmailActionIn,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(check_public_rate)],
) -> dict[str, str]:
    """Canjea un enlace de tarjeta de un solo uso por una cookie HttpOnly."""
    action = card_access_service.consume_email_token(session, data.token, "card_access")
    member = session.get(Member, action.member_id)
    merchant = session.get(Merchant, action.merchant_id)
    if member is None or merchant is None or member.email_verified_at is None:
        raise DomainError(400, "invalid_or_expired_link", "El enlace no es válido o ha caducado.")
    raw_session = card_access_service.create_card_session(session, member.id, action.merchant_id)
    session.commit()
    _set_card_cookie(response, raw_session, settings)
    return {"merchant_slug": merchant.slug}


@router.get("/public/card-access/{merchant_slug}", response_model=list[CardAccessOut])
def get_member_cards(
    merchant_slug: str,
    session: DbSession,
    card_session: str | None = Cookie(default=None, alias="lf_member_card"),
    _: Annotated[None, Depends(check_public_read_rate)] = None,
) -> list[CardAccessOut]:
    """Devuelve solo las tarjetas del comercio vinculado a la cookie privada."""
    from fastapi import HTTPException

    if card_session is None:
        raise HTTPException(status_code=401, detail="Solicita un enlace de acceso por correo.")
    member, _merchant = card_access_service.card_session_member(
        session, card_session, merchant_slug
    )
    return [
        CardAccessOut(**item)
        for item in card_access_service.cards_for_member(session, member.id)
        if item["merchant_slug"] == merchant_slug
    ]


@router.post("/public/card-access/{merchant_slug}/logout", status_code=200)
def logout_member_cards(
    merchant_slug: str,
    response: Response,
    session: DbSession,
    card_session: str | None = Cookie(default=None, alias="lf_member_card"),
) -> dict[str, str]:
    if card_session is not None:
        card_access_service.revoke_card_session(session, card_session, merchant_slug)
        session.commit()
    response.delete_cookie("lf_member_card", path="/api/v1/public", httponly=True)
    return {"message": "Sesión cerrada."}


def _set_card_cookie(response: Response, raw: str, settings: Settings) -> None:
    response.set_cookie(
        "lf_member_card",
        raw,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
        path="/api/v1/public",
    )


@router.get("/public/memberships/{token}", response_model=PublicMembershipOut)
def public_card(
    token: str,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(check_public_read_rate)],
) -> PublicMembershipOut:
    """Tarjeta web del cliente: fallback sin Wallet y consulta del saldo (§6.7).

    Se consulta también por **sondeo** desde la propia página para reflejar
    sellos y cambios de estado sin recargar (límite de lectura generoso).
    """
    payload = members_service.public_card_payload(session, token, settings)
    return PublicMembershipOut(**payload)  # type: ignore[arg-type]


@router.get("/public/memberships/{token}/qr")
def public_card_qr(
    token: str,
    request: Request,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(check_public_read_rate)],
) -> Response:
    """QR (SVG) de la propia tarjeta para enseñarlo en el mostrador (§6.7, §14.1).

    El contenido es la **URL absoluta** de la tarjeta: al escanearla con un
    móvil se abre la tarjeta, y el personal puede pegarla igualmente en el
    buscador de operaciones (que extrae el código de la URL). Nunca expone
    datos personales: solo el token opaco dentro de la ruta.
    """
    membership = members_service.membership_by_token(session, token)
    if membership.status != "active":
        raise DomainError(403, "membership_inactive", "Esta tarjeta está desactivada")
    import segno

    base = resolve_public_base(request, settings)
    content = absolute_url(f"/card/{membership.public_token}", base)
    qr = segno.make(content, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=6, border=2)
    return Response(
        content=buffer.getvalue(),
        media_type="image/svg+xml",
        headers={"X-QR-Content": content},
    )


@router.get("/merchants/{merchant_id}/members", response_model=list[MemberOut])
def list_members(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantAdminDep,  # noqa: ARG001
) -> list[MemberOut]:
    """Clientes del comercio (solo administración del comercio, §8.2)."""
    return [MemberOut.model_validate(m) for m in members_service.list_members(session, merchant_id)]


@router.get("/merchants/{merchant_id}/memberships", response_model=list[MembershipOut])
def list_memberships(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantAdminDep,  # noqa: ARG001
    q: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
) -> list[MembershipOut]:
    """Tarjetas del comercio; `q` filtra por nombre o correo del cliente (§13.5)."""
    rows = members_service.list_memberships(session, merchant_id, q=q)
    return members_service.to_outs(session, merchant_id, rows)


@router.get(
    "/merchants/{merchant_id}/memberships/search",
    response_model=list[MembershipOut],
)
def search_memberships(
    merchant_id: uuid.UUID,
    q: Annotated[str, Query(min_length=2, max_length=120)],
    session: DbSession,
    context: OperatorDep,
) -> list[MembershipOut]:
    """Búsqueda por nombre/correo del cliente para el mostrador (§13.5).

    Para cuando el cliente no tiene el móvil a mano: el personal autorizado
    localiza su tarjeta y le da sellos igual. Está permitida a roles
    operativos (owner/admin/staff) porque es una función de mostrador, y
    **queda registrada en la auditoría** como exige la política de privacidad.
    """
    rows = members_service.search_memberships(session, merchant_id, q)
    record_audit(
        session,
        action="member.searched",
        entity_type="membership",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        # Solo el hash del término: la auditoría no guarda PII (§16.6).
        metadata={"term_hash": hashlib.sha256(q.strip().lower().encode("utf-8")).hexdigest()},
    )
    session.commit()
    return members_service.to_outs(session, merchant_id, rows)


@router.get(
    "/merchants/{merchant_id}/members/{member_id}/cards",
    response_model=list[MembershipOut],
)
def list_member_cards(
    merchant_id: uuid.UUID,
    member_id: uuid.UUID,
    session: DbSession,
    context: OperatorDep,  # noqa: ARG001
) -> list[MembershipOut]:
    """Todas las tarjetas de un cliente del comercio (§13.5).

    El mostrador la usa tras identificar la tarjeta para elegir la promoción
    correcta cuando el cliente está en varios programas a la vez.
    """
    rows = members_service.list_member_cards(session, merchant_id, member_id)
    return members_service.to_outs(session, merchant_id, rows)


class LifecycleActionIn(BaseModel):
    """Motivo opcional de una acción de ciclo de vida (ADR-0005)."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=255)


def _scoped_membership(
    session: Session, merchant_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership:
    """Membresía del comercio; la ajena responde igual que la inexistente (§8.2)."""
    membership = session.get(Membership, membership_id)
    if membership is None or membership.merchant_id != merchant_id:
        raise DomainError(404, "membership_not_found", "Membresía no encontrada")
    return membership


@router.post(
    "/merchants/{merchant_id}/memberships/{membership_id}/suspend",
    response_model=MembershipOut,
)
def suspend_membership(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: LifecycleActionIn,
    session: DbSession,
    context: MerchantAdminDep,
) -> MembershipOut:
    """Suspende la tarjeta: deja de sumar y canjear de inmediato (ADR-0005)."""
    membership = _scoped_membership(session, merchant_id, membership_id)
    lifecycle.suspend(session, membership, actor_id=context.user.id, reason=data.reason)
    session.commit()
    return MembershipOut.model_validate(membership)


@router.post(
    "/merchants/{merchant_id}/memberships/{membership_id}/reactivate",
    response_model=MembershipOut,
)
def reactivate_membership(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: LifecycleActionIn,
    session: DbSession,
    context: MerchantAdminDep,
) -> MembershipOut:
    membership = _scoped_membership(session, merchant_id, membership_id)
    lifecycle.reactivate(session, membership, actor_id=context.user.id, reason=data.reason)
    session.commit()
    return MembershipOut.model_validate(membership)


@router.post(
    "/merchants/{merchant_id}/memberships/{membership_id}/revoke",
    response_model=MembershipOut,
)
def revoke_membership(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: LifecycleActionIn,
    session: DbSession,
    context: MerchantAdminDep,
) -> MembershipOut:
    """Revocación definitiva. No promete borrar el pase del móvil (ADR-0005)."""
    membership = _scoped_membership(session, merchant_id, membership_id)
    lifecycle.revoke(session, membership, actor_id=context.user.id, reason=data.reason)
    session.commit()
    return MembershipOut.model_validate(membership)


@router.post(
    "/merchants/{merchant_id}/memberships/{membership_id}/request-deletion",
    response_model=MembershipOut,
)
def request_membership_deletion(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: LifecycleActionIn,
    session: DbSession,
    context: MerchantAdminDep,
) -> MembershipOut:
    """Solicitud de supresión de datos; se ejecuta con `anonymize`."""
    membership = _scoped_membership(session, merchant_id, membership_id)
    lifecycle.request_deletion(session, membership, actor_id=context.user.id, reason=data.reason)
    session.commit()
    return MembershipOut.model_validate(membership)


@router.post(
    "/merchants/{merchant_id}/memberships/{membership_id}/anonymize",
    response_model=MembershipOut,
)
def anonymize_membership(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: LifecycleActionIn,
    session: DbSession,
    context: MerchantAdminDep,
) -> MembershipOut:
    """Ejecuta la supresión: anonimiza datos y conserva el ledger (§7.3)."""
    membership = _scoped_membership(session, merchant_id, membership_id)
    lifecycle.anonymize(session, membership, actor_id=context.user.id)
    session.commit()
    return MembershipOut.model_validate(membership)


@router.get("/public/memberships/{token}/wallet-options")
def public_wallet_options(
    token: str,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(check_public_read_rate)],
) -> dict[str, object]:
    """Opciones reales de Wallet para el cliente (§6.7): sin falsas promesas.

    `simulated=true` significa que el proveedor es el simulador de desarrollo:
    la interfaz lo rotula como modo demostración y ofrece la tarjeta web.
    """
    membership = members_service.membership_by_token(session, token)
    actions, simulated = wallet_service.add_to_wallet_actions(session, membership, settings)
    provider = get_wallet_provider(settings)
    return {
        "provider": provider.name,
        "provider_status": provider.status().value,
        "simulated": simulated,
        "actions": [
            {
                "kind": action.kind,
                "label": action.label,
                "url": action.url,
                "simulated": action.simulated,
            }
            for action in actions
        ],
    }


@router.get("/public/memberships/{token}/apple-pass")
def public_apple_pass(
    token: str,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Descarga del `.pkpass` firmado (FASE 5). Solo con credenciales reales."""
    membership = members_service.membership_by_token(session, token)
    lifecycle.ensure_operable(membership)
    provider = get_wallet_provider(settings)
    if not isinstance(provider, AppleWalletProvider) or provider.status().value == "not_configured":
        raise DomainError(409, "wallet_provider_not_configured", "Apple Wallet no está configurado")
    context = wallet_service.pass_context(session, membership, settings)
    try:
        data = provider.build_pass(context)
    except PassBuildError as error:
        raise DomainError(409, "wallet_issue_failed", str(error)) from error
    return Response(
        content=data,
        media_type="application/vnd.apple.pkpass",
        headers={
            "Content-Disposition": f'attachment; filename="{context.serial}.pkpass"',
        },
    )


@router.get("/public/memberships/{token}/google-save")
def public_google_save(
    token: str,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Redirige al enlace oficial «Save to Google Wallet» (FASE 6)."""
    membership = members_service.membership_by_token(session, token)
    lifecycle.ensure_operable(membership)
    provider = get_wallet_provider(settings)
    if (
        not isinstance(provider, GoogleWalletProvider)
        or provider.status().value == "not_configured"
    ):
        raise DomainError(
            409, "wallet_provider_not_configured", "Google Wallet no está configurado"
        )
    context = wallet_service.pass_context(session, membership, settings)
    try:
        url = provider.build_save_url(context, membership.public_token)
    except PassBuildError as error:
        raise DomainError(409, "wallet_issue_failed", str(error)) from error
    return RedirectResponse(url, status_code=302)
