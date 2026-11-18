"""Servicio de altas públicas y consultas de membresía (§12.5, §13.4).

Reglas:
- El alta solo funciona con el programa **activo** (§7.2).
- El token es opaco y aleatorio: no codifica email, saldo ni IDs (§5.2, §9.3).
- Un email repetido en el mismo comercio no duplica membresía del mismo
  programa: se responde con un error claro (sin filtrar datos).
"""

import secrets
import uuid
from typing import Any

from sqlalchemy import Exists, Select, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import DomainError
from app.models.ledger import LoyaltyTransaction, TransactionType
from app.models.loyalty import LoyaltyProgram, ProgramReward, ProgramStatus
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.user import utcnow
from app.schemas.members import ManualEnrollIn, MembershipOut, MembershipPage, MemberUpdateIn
from app.services.audit import record_audit
from app.services.expiry import expire_due_stamps
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


def manual_enroll(
    session: Session,
    merchant_id: uuid.UUID,
    data: ManualEnrollIn,
    actor_user_id: uuid.UUID,
) -> tuple[Membership, bool]:
    """Alta en mostrador (§13.5): el personal crea la tarjeta en el local.

    Diferencias con el alta pública (ADR-0006):
    - El email es **opcional** (minimización): sin email, la tarjeta se
      recupera por su enlace/código, que solo muestra el mostrador.
    - El email, si se recoge, queda **sin verificar**: nadie ha demostrado
      control del buzón. La verificación posterior habilita la recuperación
      por email, nunca la creación.
    - La tarjeta nace **activa y usable al instante**: no hay paso de
      verificación entre el alta y el primer sello.
    - Si el cliente ya tenía tarjeta en ese programa, se devuelve la suya
      (`created=False`): mostrador idempotente, sin duplicados.
    """
    program = session.get(LoyaltyProgram, data.program_id)
    if program is None or program.merchant_id != merchant_id:
        raise DomainError(404, "program_not_found", "Programa no encontrado")
    if program.status != ProgramStatus.ACTIVE:
        raise DomainError(409, "program_not_active", "El programa no está aceptando altas")
    if data.accepted_terms_version != program.terms_version:
        raise DomainError(
            409,
            "terms_version_mismatch",
            "Las condiciones han cambiado: recarga la página y revísalas de nuevo",
        )

    normalized_name = " ".join(data.display_name.split())
    if not normalized_name:
        raise DomainError(422, "invalid_display_name", "El nombre es obligatorio")

    normalized_email = data.email.strip().lower() if data.email else None
    member: Member | None = None
    if normalized_email:
        member = session.scalar(
            select(Member).where(
                Member.merchant_id == merchant_id, Member.email == normalized_email
            )
        )
    if member is None:
        member = Member(
            merchant_id=merchant_id,
            email=normalized_email,
            display_name=normalized_name,
            privacy_notice_version=data.privacy_notice_version,
        )
        session.add(member)
        session.flush()

    existing_membership = session.scalar(
        select(Membership).where(
            Membership.member_id == member.id, Membership.program_id == program.id
        )
    )
    if existing_membership is not None:
        return existing_membership, False

    membership = Membership(
        merchant_id=merchant_id,
        program_id=program.id,
        member_id=member.id,
        public_token=new_public_token(),
        terms_version_accepted=program.terms_version,
        origin="counter",
    )
    session.add(membership)
    session.flush()
    record_audit(
        session,
        action="membership.manual_enroll",
        entity_type="membership",
        entity_id=str(membership.id),
        actor_id=actor_user_id,
        merchant_id=merchant_id,
    )
    return membership, True


def update_member(
    session: Session, merchant_id: uuid.UUID, membership_id: uuid.UUID, data: MemberUpdateIn
) -> Membership:
    """Edición de datos mínimos del cliente (decisión de compra #9).

    Nombre y correo, nada más (§9.3). Cambiar el correo lo deja **sin
    verificar** y respeta el único email por comercio (`uq_member_email`);
    un cliente ya anonimizado no se toca. La membresía ajena responde 404
    igual que la inexistente (§8.2).
    """
    membership = session.get(Membership, membership_id)
    if membership is None or membership.merchant_id != merchant_id:
        raise DomainError(404, "membership_not_found", "Membresía no encontrada")
    member = session.get(Member, membership.member_id)
    if member is None or member.merchant_id != merchant_id:
        raise DomainError(404, "member_not_found", "Cliente no encontrado")
    if member.anonymized_at is not None:
        raise DomainError(409, "member_anonymized", "El cliente fue eliminado y no se puede editar")

    if data.display_name is not None:
        member.display_name = data.display_name.strip()

    if data.email is not None:
        normalized = str(data.email).strip().lower()
        if normalized != (member.email or ""):
            duplicate = session.scalar(
                select(Member).where(
                    Member.merchant_id == merchant_id,
                    Member.email == normalized,
                    Member.id != member.id,
                )
            )
            if duplicate is not None:
                raise DomainError(409, "email_taken", "Ya existe otro cliente con ese correo")
            member.email = normalized
            # El nuevo buzón no está verificado: vuelve al circuito normal
            # de verificación si el comercio o el cliente lo necesitan.
            member.email_verified_at = None

    session.flush()
    return membership


def membership_by_token(session: Session, token: str) -> Membership:
    membership = session.scalar(select(Membership).where(Membership.public_token == token))
    if membership is None:
        raise DomainError(404, "membership_not_found", "Tarjeta no encontrada")
    member = session.get(Member, membership.member_id)
    # La verificación de email es requisito del alta pública (ADR-0006): ahí
    # el buzón es la prueba de identidad. En el alta en mostrador el ancla es
    # la entrega presencial (origin="counter"): el email, registrado sin
    # verificar solo para identificar al cliente, no bloquea la tarjeta.
    unverified = (
        member is not None and member.email is not None and member.email_verified_at is None
    )
    if unverified and membership.origin != "counter":
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
    # La tarjeta muestra el saldo vigente: los sellos vencidos se aplican
    # antes de leerlo (§7.7; coste cero cuando no hay regla).
    expire_due_stamps(session, membership, program)
    # Registro propio del cliente (§9.3: minimización): solo el número de
    # visitas y la última. Nada de importes, notas ni detalle de operaciones.
    visit_row = session.execute(
        select(func.count(LoyaltyTransaction.id), func.max(LoyaltyTransaction.created_at)).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EARN,
        )
    ).one()
    last_visit = visit_row[1]
    from app.services import branding as branding_service

    branding = branding_service.out_payload(
        session, branding_service.get_or_create(session, membership.merchant_id)
    )
    return {
        "merchant_name": merchant.name,
        "program_name": program.name,
        "program_type": program.program_type,
        "stamps": membership.stamps,
        "status": membership.status,
        # Condición de caducidad si la hay: la tarjeta la comunica (§7.7).
        "stamps_expire_days": program.stamps_expire_days,
        "rewards": [
            {
                "name": reward.name,
                "stamps_required": reward.stamps_required,
                "earned": membership.stamps >= reward.stamps_required,
            }
            for reward in sorted(rewards, key=lambda r: r.stamps_required)
        ],
        "total_visits": int(visit_row[0] or 0),
        "last_visit_at": last_visit.isoformat() if last_visit else None,
        # Rotulado honesto (§17.2, ADR-0002): sin credenciales no hay pase real.
        "wallet_options": [],
        "simulated_wallet": settings.wallet_provider == "simulated",
        "primary_color": branding["primary_color"],
        "accent_color": branding["accent_color"],
        "stamp_icon": branding["stamp_icon"],
        "footer_text": branding["footer_text"],
        "logo_url": branding["logo_url"],
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


def _membership_query(
    merchant_id: uuid.UUID,
    program_id: uuid.UUID | None = None,
    q: str | None = None,
    ready: bool = False,
) -> Select[Membership]:
    """Consulta base del listado, con los filtros compartidos aplicados.

    `ready` filtra por recompensa activa ya alcanzable con el saldo actual
    (insignia «Premio listo»): un `EXISTS` correlacionado con el catálogo,
    nunca calculado en cliente.
    """
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
    if ready:
        query = query.where(_ready_exists())
    return query


def _ready_exists() -> Exists:
    """Alguna recompensa **activa** alcanzable con los sellos actuales."""
    return exists(
        select(ProgramReward.id)
        .where(
            ProgramReward.program_id == Membership.program_id,
            ProgramReward.status == "active",
            ProgramReward.stamps_required <= Membership.stamps,
        )
        .correlate(Membership)
    )


def list_memberships(
    session: Session,
    merchant_id: uuid.UUID,
    program_id: uuid.UUID | None = None,
    q: str | None = None,
) -> list[Membership]:
    rows = session.scalars(_membership_query(merchant_id, program_id=program_id, q=q)).all()
    return sorted(rows, key=lambda m: m.joined_at, reverse=True)


def page_memberships(
    session: Session,
    merchant_id: uuid.UUID,
    *,
    q: str | None = None,
    ready: bool = False,
    limit: int = 25,
    offset: int = 0,
) -> MembershipPage:
    """Página del listado con los contadores reales (§13.2, escala).

    Devuelve `items` ordenados por alta reciente, `total` (con los filtros
    aplicados) y los contadores globales por estado que la cabecera de la
    pantalla rotula. Todo desde la base de datos: ningún contador se inventa
    en cliente. Paginación limit/offset por orden estable (`joined_at`
    desc, desempate por id) para que una alta nueva no desplace páginas.
    """
    base_all = _membership_query(merchant_id, q=q)
    base = base_all.where(_ready_exists()) if ready else base_all
    ordered = base.order_by(Membership.joined_at.desc(), Membership.id).offset(offset).limit(limit)
    items = list(session.scalars(ordered).all())

    def _count(source: Select[Membership], extra: Any = None) -> int:
        stmt = select(func.count()).select_from(source.subquery())
        if extra is not None:
            stmt = select(func.count()).select_from(source.where(extra).subquery())
        return int(session.scalar(stmt) or 0)

    return MembershipPage(
        items=to_outs(session, merchant_id, items),
        total=_count(base),
        active=_count(base, Membership.status == "active"),
        suspended=_count(base, Membership.status == "suspended"),
        # Etiqueta del chip «Premio listo»: recuento global (con `q`, sin el
        # propio filtro), para que no cambie al activar el chip.
        ready=_count(base_all, _ready_exists()),
    )


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
    program = session.get(LoyaltyProgram, membership.program_id)
    # Ficha al día: los sellos vencidos se materializan antes de leer el
    # saldo que verá el cliente o el mostrador (§7.7; coste cero sin regla).
    expire_due_stamps(session, membership, program)
    out = MembershipOut.model_validate(membership)
    if program is not None:
        out.program_name = program.name
        out.program_type = program.program_type
    member = session.get(Member, membership.member_id)
    if member is not None and member.merchant_id == merchant_id:
        out.member_name = member.display_name
        out.member_email = member.email
    rewards = list(
        session.scalars(
            select(ProgramReward).where(
                ProgramReward.program_id == membership.program_id,
                ProgramReward.status == "active",
            )
        )
    )
    _apply_reward_info(out, rewards)
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
        program.id: program
        for program in session.scalars(
            select(LoyaltyProgram).where(LoyaltyProgram.id.in_(program_ids))
        )
    }
    # Recompensas activas de los programas implicados, agrupadas en una sola
    # consulta: la insignia «Premio listo» se deriva del catálogo real.
    rewards_by_program: dict[uuid.UUID, list[ProgramReward]] = {}
    for reward in session.scalars(
        select(ProgramReward).where(
            ProgramReward.program_id.in_(program_ids), ProgramReward.status == "active"
        )
    ):
        rewards_by_program.setdefault(reward.program_id, []).append(reward)
    outs: list[MembershipOut] = []
    for row in memberships:
        program = programs.get(row.program_id)
        # Vencidos aplicados antes de serializar el saldo (coste cero si
        # el programa no define caducidad).
        expire_due_stamps(session, row, program)
        out = MembershipOut.model_validate(row)
        if program is not None:
            out.program_name = program.name
            out.program_type = program.program_type
        member = members.get(row.member_id)
        if member is not None:
            out.member_name = member.display_name
            out.member_email = member.email
        _apply_reward_info(out, rewards_by_program.get(row.program_id, []))
        outs.append(out)
    return outs


def _apply_reward_info(out: MembershipOut, rewards: list[ProgramReward]) -> None:
    """Rellena `next_reward_*` y `reward_ready` del catálogo activo.

    «Premio listo» = alguna recompensa activa ya alcanzable con el saldo
    actual. Si no hay ninguna lista, los campos quedan nulos: el mostrador
    no inventa progresos (§6.1).
    """
    if not rewards:
        return
    reachable = [reward for reward in rewards if reward.stamps_required <= out.stamps]
    ahead = [reward for reward in rewards if reward.stamps_required > out.stamps]
    if reachable:
        out.reward_ready = True
        nearest_done = min(reachable, key=lambda reward: reward.stamps_required)
        out.next_reward_name = nearest_done.name
        out.next_reward_remaining = 0
        return
    if ahead:
        nearest = min(ahead, key=lambda reward: reward.stamps_required)
        out.next_reward_name = nearest.name
        out.next_reward_remaining = nearest.stamps_required - out.stamps


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
