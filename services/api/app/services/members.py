"""Servicio de altas públicas y consultas de membresía (§12.5, §13.4).

Reglas:
- El alta solo funciona con el programa **activo** (§7.2).
- El token es opaco y aleatorio: no codifica email, saldo ni IDs (§5.2, §9.3).
- Un email repetido en el mismo comercio no duplica membresía del mismo
  programa: se responde con un error claro (sin filtrar datos).
"""

import secrets
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import DomainError
from app.models.loyalty import LoyaltyProgram, ProgramReward, ProgramStatus
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.user import utcnow
from app.schemas.members import MembershipOut
from app.services.lifecycle import ensure_operable


def new_public_token() -> str:
    return secrets.token_hex(32)


def _program_by_slug(
    session: Session, merchant_slug: str, program_slug: str
) -> tuple[Merchant, LoyaltyProgram]:
    merchant = session.scalar(select(Merchant).where(Merchant.slug == merchant_slug))
    if merchant is None:
        raise DomainError(404, "program_not_found", "Programa no encontrado")
    program = session.scalar(
        select(LoyaltyProgram).where(
            LoyaltyProgram.merchant_id == merchant.id, LoyaltyProgram.slug == program_slug
        )
    )
    if program is None:
        raise DomainError(404, "program_not_found", "Programa no encontrado")
    return merchant, program


def enroll(
    session: Session,
    merchant_slug: str,
    program_slug: str,
    email: str,
    display_name: str,
    accepted_terms_version: int,
    privacy_notice_version: int,
    marketing_consent: bool = False,
) -> tuple[Membership, Merchant, LoyaltyProgram, bool]:
    """Alta pública (ADR-0006): nombre completo y email obligatorios.

    - Email normalizado (`trim` + minúsculas) para duplicados y búsquedas.
    - Nombre normalizado (espacios colapsados) sin alterar nombres propios.
    - Consentimientos registrados: condiciones versionadas, aviso de
      privacidad con su versión y marketing **opcional** (la elección se
      guarda tal cual se hizo en este alta).

    Devuelve además `created`: True solo cuando se ha creado una membresía
    nueva. La auditoría de altas usa esa señal para no duplicar eventos con
    solicitudes repetidas de un alta ya existente (idempotencia pública).
    """
    merchant, program = _program_by_slug(session, merchant_slug, program_slug)
    if program.status != ProgramStatus.ACTIVE:
        raise DomainError(409, "program_not_active", "El programa no está aceptando altas")
    if accepted_terms_version != program.terms_version:
        raise DomainError(
            409,
            "terms_version_mismatch",
            "Las condiciones han cambiado: recarga la página y revísalas de nuevo",
        )

    normalized_email = email.strip().lower()
    normalized_name = " ".join(display_name.split())
    if not normalized_name:
        raise DomainError(422, "invalid_display_name", "El nombre completo es obligatorio")

    existing_member = session.scalar(
        select(Member).where(Member.merchant_id == merchant.id, Member.email == normalized_email)
    )
    now = utcnow()
    if existing_member is None:
        member = Member(
            merchant_id=merchant.id,
            email=normalized_email,
            display_name=normalized_name,
            privacy_notice_version=privacy_notice_version,
            marketing_consent=1 if marketing_consent else 0,
            marketing_consent_at=now if marketing_consent else None,
        )
        session.add(member)
        session.flush()
    else:
        member = existing_member
        # Un alta no verificada no puede modificar los datos ni consentimientos
        # de una identidad ya existente. La verificación confirma control del buzón.
        session.flush()

    existing_membership = session.scalar(
        select(Membership).where(
            Membership.member_id == member.id, Membership.program_id == program.id
        )
    )
    if existing_membership is not None:
        return existing_membership, merchant, program, False

    membership = Membership(
        merchant_id=merchant.id,
        program_id=program.id,
        member_id=member.id,
        public_token=new_public_token(),
        terms_version_accepted=program.terms_version,
    )
    session.add(membership)
    session.flush()
    return membership, merchant, program, True


def membership_by_token(session: Session, token: str) -> Membership:
    membership = session.scalar(select(Membership).where(Membership.public_token == token))
    if membership is None:
        raise DomainError(404, "membership_not_found", "Tarjeta no encontrada")
    member = session.get(Member, membership.member_id)
    if member is None or (member.email is not None and member.email_verified_at is None):
        raise DomainError(403, "email_not_verified", "Confirma tu correo para abrir esta tarjeta.")
    return membership


def public_card_payload(session: Session, token: str, settings: Settings) -> dict[str, object]:
    """Datos de la tarjeta web del cliente (fallback sin Wallet, §6.7)."""
    membership = membership_by_token(session, token)
    ensure_operable(membership)
    merchant = session.get(Merchant, membership.merchant_id)
    program = session.get(LoyaltyProgram, membership.program_id)
    if merchant is None or program is None:
        raise DomainError(404, "membership_not_found", "Tarjeta no encontrada")

    rewards = session.scalars(
        select(ProgramReward).where(
            ProgramReward.program_id == program.id, ProgramReward.status == "active"
        )
    ).all()
    return {
        "merchant_name": merchant.name,
        "program_name": program.name,
        "program_type": program.program_type,
        "stamps": membership.stamps,
        "status": membership.status,
        "rewards": [
            {
                "name": reward.name,
                "stamps_required": reward.stamps_required,
                "earned": membership.stamps >= reward.stamps_required,
            }
            for reward in sorted(rewards, key=lambda r: r.stamps_required)
        ],
        # Rotulado honesto (§17.2, ADR-0002): sin credenciales no hay pase real.
        "wallet_options": [],
        "simulated_wallet": settings.wallet_provider == "simulated",
    }


def list_members(session: Session, merchant_id: uuid.UUID) -> list[Member]:
    """Clientes visibles: los anonimizados ya no son «clientes» (§9.5)."""
    rows = session.scalars(
        select(Member).where(
            Member.merchant_id == merchant_id,
            Member.anonymized_at.is_(None),
        )
    ).all()
    return sorted(rows, key=lambda m: m.created_at, reverse=True)


def list_memberships(
    session: Session,
    merchant_id: uuid.UUID,
    program_id: uuid.UUID | None = None,
    q: str | None = None,
) -> list[Membership]:
    # Las membresías eliminadas (anonimizadas) dejan de listarse: el cliente
    # borrado no debe seguir apareciendo. `deletion_pending` sí se muestra
    # para que se complete la supresión pendiente (ADR-0005, enmienda).
    query = select(Membership).where(
        Membership.merchant_id == merchant_id,
        Membership.status != "anonymized",
    )
    if program_id is not None:
        query = query.where(Membership.program_id == program_id)
    if q is not None and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            Membership.member_id.in_(
                select(Member.id).where(
                    Member.merchant_id == merchant_id,
                    or_(Member.email.ilike(term), Member.display_name.ilike(term)),
                )
            )
        )
    rows = session.scalars(query).all()
    return sorted(rows, key=lambda m: m.joined_at, reverse=True)


def search_memberships(
    session: Session, merchant_id: uuid.UUID, term: str, limit: int = 10
) -> list[Membership]:
    """Tarjetas cuyo cliente coincide por nombre o correo (mostrador, §13.5).

    Búsqueda por igualdad difusa dentro del propio comercio; nunca devuelve
    tarjetas de otro comercio (§8.2).
    """
    pattern = f"%{term.strip()}%"
    stmt = (
        select(Membership)
        .join(Member, Membership.member_id == Member.id)
        .where(
            Membership.merchant_id == merchant_id,
            Member.merchant_id == merchant_id,
            or_(Member.email.ilike(pattern), Member.display_name.ilike(pattern)),
        )
        .order_by(Membership.joined_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def to_out(session: Session, merchant_id: uuid.UUID, membership: Membership) -> MembershipOut:
    """Salida enriquecida con el programa y la identidad mínima (§13.5)."""
    out = MembershipOut.model_validate(membership)
    out.program_name = _program_name(session, membership.program_id)
    member = session.get(Member, membership.member_id)
    if member is not None and member.merchant_id == merchant_id:
        out.member_name = member.display_name
        out.member_email = member.email
    return out


def to_outs(
    session: Session, merchant_id: uuid.UUID, memberships: list[Membership]
) -> list[MembershipOut]:
    """Igual que `to_out` para listados, con consultas agrupadas."""
    if not memberships:
        return []
    member_ids = {row.member_id for row in memberships}
    program_ids = {row.program_id for row in memberships}
    members = {
        member.id: member
        for member in session.scalars(
            select(Member).where(Member.merchant_id == merchant_id, Member.id.in_(member_ids))
        )
    }
    programs = {
        program.id: program.name
        for program in session.scalars(
            select(LoyaltyProgram).where(LoyaltyProgram.id.in_(program_ids))
        )
    }
    outs: list[MembershipOut] = []
    for row in memberships:
        out = MembershipOut.model_validate(row)
        program_name = programs.get(row.program_id)
        if program_name is not None:
            out.program_name = program_name
        member = members.get(row.member_id)
        if member is not None:
            out.member_name = member.display_name
            out.member_email = member.email
        outs.append(out)
    return outs


def list_member_cards(
    session: Session, merchant_id: uuid.UUID, member_id: uuid.UUID
) -> list[Membership]:
    """Todas las tarjetas (programas) de un cliente del comercio (§13.5).

    Permite al mostrador elegir la promoción correcta cuando el cliente tiene
    varias. Un miembro de otro comercio responde 404 igual que uno inexistente.
    """
    member = session.scalar(
        select(Member).where(Member.id == member_id, Member.merchant_id == merchant_id)
    )
    if member is None:
        raise DomainError(404, "member_not_found", "Cliente no encontrado")
    rows = session.scalars(
        select(Membership).where(
            Membership.member_id == member_id,
            Membership.merchant_id == merchant_id,
        )
    ).all()
    return sorted(rows, key=lambda m: m.joined_at, reverse=True)


def _program_name(session: Session, program_id: uuid.UUID) -> str | None:
    program = session.get(LoyaltyProgram, program_id)
    return program.name if program is not None else None
