"""Ciclo de vida de la membresía y de la tarjeta (ADR-0005).

Transiciones validadas en **backend** (ocultar un botón no es control de
acceso):

    active → suspended → active (reactivar)
    active | suspended → revoked (definitivo)
    active | suspended | revoked → deletion_pending → anonymized

Reglas irrenunciables:

- Suspender/revocar **bloquea inmediatamente** earn/redeem en el servidor,
  sin esperar a que ninguna Wallet sincronice (el ledger manda, §6.1).
- La eliminación **anonimiza** los datos personales y conserva el ledger
  asociado a la membresía (nunca se borran movimientos: §7.3).
- Cada transición queda auditada con actor, estado anterior/nuevo y motivo.
- Ninguna acción promete borrar la tarjeta del móvil del cliente: eso depende
  de Apple/Google (ADR-0005). La interfaz usa los verbos exactos.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DomainError
from app.models.members import Member, Membership
from app.models.user import utcnow
from app.services.audit import record_audit

ACTIVE = "active"
SUSPENDED = "suspended"
REVOKED = "revoked"
DELETION_PENDING = "deletion_pending"
ANONYMIZED = "anonymized"

MEMBERSHIP_STATUSES = (ACTIVE, SUSPENDED, REVOKED, DELETION_PENDING, ANONYMIZED)


def _transition(
    session: Session,
    membership: Membership,
    *,
    new_status: str,
    allowed_from: tuple[str, ...],
    action: str,
    actor_id: uuid.UUID | None,
    reason: str | None,
) -> Membership:
    previous = membership.status
    if previous == new_status:
        raise DomainError(
            409, "invalid_status_transition", f"La tarjeta ya está en estado «{previous}»"
        )
    if previous not in allowed_from:
        raise DomainError(
            409,
            "invalid_status_transition",
            f"No se puede pasar de «{previous}» a «{new_status}»",
        )
    membership.status = new_status
    membership.status_reason = (reason.strip()[:255] if reason else None) or None
    membership.status_changed_at = utcnow()
    if new_status == DELETION_PENDING:
        membership.deletion_requested_at = utcnow()
    if new_status == ANONYMIZED:
        membership.anonymized_at = utcnow()
    record_audit(
        session,
        action=action,
        entity_type="membership",
        actor_id=actor_id,
        merchant_id=membership.merchant_id,
        entity_id=str(membership.id),
        metadata={
            "previous_status": previous,
            "new_status": new_status,
            "reason": membership.status_reason or "",
        },
    )
    session.flush()
    return membership


def suspend(
    session: Session,
    membership: Membership,
    *,
    actor_id: uuid.UUID | None,
    reason: str | None = None,
) -> Membership:
    """Pausa temporal: no suma ni canjea. Reversible con `reactivate`."""
    return _transition(
        session,
        membership,
        new_status=SUSPENDED,
        allowed_from=(ACTIVE,),
        action="membership.suspended",
        actor_id=actor_id,
        reason=reason,
    )


def reactivate(
    session: Session,
    membership: Membership,
    *,
    actor_id: uuid.UUID | None,
    reason: str | None = None,
) -> Membership:
    """Reactiva una membresía suspendida (no una revocada ni anonimizada)."""
    return _transition(
        session,
        membership,
        new_status=ACTIVE,
        allowed_from=(SUSPENDED,),
        action="membership.reactivated",
        actor_id=actor_id,
        reason=reason,
    )


def revoke(
    session: Session,
    membership: Membership,
    *,
    actor_id: uuid.UUID | None,
    reason: str | None = None,
) -> Membership:
    """Baja definitiva del programa: bloqueo permanente de operaciones."""
    return _transition(
        session,
        membership,
        new_status=REVOKED,
        allowed_from=(ACTIVE, SUSPENDED),
        action="membership.revoked",
        actor_id=actor_id,
        reason=reason,
    )


def request_deletion(
    session: Session,
    membership: Membership,
    *,
    actor_id: uuid.UUID | None,
    reason: str | None = None,
) -> Membership:
    """Registra la solicitud de supresión de datos (se ejecuta con `anonymize`)."""
    return _transition(
        session,
        membership,
        new_status=DELETION_PENDING,
        allowed_from=(ACTIVE, SUSPENDED, REVOKED),
        action="membership.deletion_requested",
        actor_id=actor_id,
        reason=reason,
    )


def anonymize(
    session: Session, membership: Membership, *, actor_id: uuid.UUID | None
) -> Membership:
    """Ejecuta la supresión: anonimiza la membresía y, si procede, al cliente.

    - La membresía pasa a `anonymized` y sus datos personales desaparecen.
    - El **ledger se conserva** referido a la membresía para no corromper la
    - integridad contable (§7.3): los movimientos quedan seudonimizados.
    - El `Member` solo se anonimiza cuando no le quedan membresías vivas.
    - El panel la ejecuta **en un solo paso** desde cualquier estado vivo
      («Eliminar cliente»); el estado `deletion_pending` queda para la vía
      API en dos pasos y los registros históricos (enmienda ADR-0005).
    """
    anonymized = _transition(
        session,
        membership,
        new_status=ANONYMIZED,
        allowed_from=(ACTIVE, SUSPENDED, REVOKED, DELETION_PENDING),
        action="membership.anonymized",
        actor_id=actor_id,
        reason=None,
    )
    others = session.scalars(
        select(Membership).where(
            Membership.member_id == membership.member_id,
            Membership.id != membership.id,
            Membership.status != ANONYMIZED,
        )
    ).all()
    if not others:
        member = session.get(Member, membership.member_id)
        if member is not None and member.anonymized_at is None:
            member.email = None
            member.display_name = None
            member.marketing_consent = 0
            member.marketing_consent_at = None
            member.anonymized_at = utcnow()
            record_audit(
                session,
                action="member.anonymized",
                entity_type="member",
                actor_id=actor_id,
                merchant_id=membership.merchant_id,
                entity_id=str(member.id),
                metadata={
                    "previous_status": member.status,
                    "new_status": "anonymized",
                    "reason": "",
                },
            )
    session.flush()
    return anonymized


def ensure_operable(membership: Membership) -> None:
    """Bloquea operaciones de valor salvo que la membresía esté activa."""
    if membership.status == ACTIVE:
        return
    if membership.status == SUSPENDED:
        raise DomainError(
            409, "membership_suspended", "Esta tarjeta está suspendida y no puede operar"
        )
    if membership.status == REVOKED:
        raise DomainError(409, "membership_revoked", "Esta tarjeta está revocada")
    raise DomainError(403, "membership_inactive", "Esta tarjeta está desactivada")
