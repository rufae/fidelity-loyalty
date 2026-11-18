"""Operaciones de fidelización: acumular, canjear y ajustar (§7.3-§7.6, §12.7).

Garantías:
- **Idempotencia**: la misma `idempotency_key` devuelve el movimiento ya
  registrado en lugar de aplicar el efecto dos veces.
- **Sin doble gasto**: el canje bloquea la fila de la membresía
  (`SELECT ... FOR UPDATE` en PostgreSQL) y verifica el saldo dentro de la
  transacción; una petición concurrente ve el saldo ya descontado.
- **Sin saldo negativo**: el canje se rechaza si no alcanza.
- **Auditoría**: cada movimiento guarda quién lo hizo y con qué motivo.
"""

import uuid
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import DomainError
from app.models.ledger import LoyaltyTransaction, RewardRedemption, TransactionType
from app.models.loyalty import LoyaltyProgram, ProgramReward, ProgramStatus, ProgramType
from app.models.members import Membership
from app.services.expiry import expire_due_stamps, stamp_expiry_after
from app.services.lifecycle import ensure_operable


@dataclass(frozen=True)
class OperationResult:
    transaction: LoyaltyTransaction
    membership: Membership
    already_applied: bool = False


def _load_membership_for_update(session: Session, membership_id: uuid.UUID) -> Membership:
    membership = session.scalar(
        select(Membership).where(Membership.id == membership_id).with_for_update()
    )
    if membership is None:
        raise DomainError(404, "membership_not_found", "Membresía no encontrada")
    # El ciclo de vida decide qué puede hacerse (ADR-0005): suspendida o
    # revocada no acumula ni canjea, aunque conserve una tarjeta Wallet.
    ensure_operable(membership)
    return membership


def _existing_by_key(
    session: Session,
    idempotency_key: str,
    *,
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> LoyaltyTransaction | None:
    """Movimiento ya registrado con esta clave **dentro del mismo comercio**.

    La clave es única globalmente, pero la búsqueda se acota por comercio y
    membresía: así una clave ajena no puede filtrar datos de otro comercio
    (§8.2 de la auditoría).
    """
    return session.scalar(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.idempotency_key == idempotency_key,
            LoyaltyTransaction.merchant_id == merchant_id,
            LoyaltyTransaction.membership_id == membership_id,
        )
    )


def _active_program(session: Session, membership: Membership) -> LoyaltyProgram:
    program = session.get(LoyaltyProgram, membership.program_id)
    if program is None:
        raise DomainError(409, "program_not_active", "El programa ya no existe")
    return program


def _earn_units(
    program: LoyaltyProgram,
    *,
    quantity: int | None,
    amount: Decimal | None,
) -> int:
    """Sellos (modo `stamps`) o puntos (modo `points`) a otorgar (§7.5-§7.6).

    En modo puntos el navegador **nunca** envía la cantidad de puntos:
    solo el importe de la venta (teclee el personal, MVP sin TPV) y el
    cálculo ocurre aquí en Decimal, redondeando hacia abajo a enteros.
    """
    if program.program_type == ProgramType.POINTS:
        if quantity is not None:
            raise DomainError(
                422,
                "invalid_quantity",
                "Este programa es de puntos: registra el importe, no sellos",
            )
        if amount is None:
            raise DomainError(422, "amount_required", "Indica el importe de la venta en euros")
        if program.points_per_euro is None:
            raise DomainError(409, "points_rule_missing", "El programa no tiene regla de puntos")
        earned = int((amount * program.points_per_euro).to_integral_value(rounding=ROUND_FLOOR))
        if earned < 1:
            raise DomainError(
                422,
                "insufficient_amount",
                "Con ese importe no se alcanza ni un punto",
            )
        if earned > 1_000_000:
            # Tope sanidad: un importe desorbitado no puede imprimir
            # millones de puntos desde el mostrador (§7.6).
            raise DomainError(422, "invalid_amount", "Importe demasiado alto")
        return earned

    if amount is not None:
        raise DomainError(
            422, "amount_not_allowed", "Este programa es de sellos: no admite importes"
        )
    units = 1 if quantity is None else quantity
    if units < 1 or units > 20:
        raise DomainError(422, "invalid_quantity", "Cantidad de sellos no válida")
    return units


def earn(
    session: Session,
    membership_id: uuid.UUID,
    merchant_id: uuid.UUID,
    *,
    quantity: int | None = None,
    amount: Decimal | None = None,
    idempotency_key: str,
    actor_user_id: uuid.UUID | None,
    reason: str | None = None,
) -> OperationResult:
    """Acumula sellos o puntos (§7.5, §7.6): unidades enteras y verificadas.

    `quantity` (1–20) es para programas de sellos; `amount` (euros, hasta
    dos decimales) para programas de puntos, donde la cantidad de puntos
    la calcula el backend con la regla del programa. Mezclar modos o
    enviar un importe inválido rechaza la operación sin registrar nada.
    """
    existing = _existing_by_key(
        session, idempotency_key, merchant_id=merchant_id, membership_id=membership_id
    )
    if existing is not None:
        membership = session.get(Membership, existing.membership_id)
        if membership is None:
            raise DomainError(409, "duplicate_operation", "Operación ya registrada")
        return OperationResult(existing, membership, already_applied=True)

    membership = _load_membership_for_update(session, membership_id)
    program = _active_program(session, membership)
    if program.status != ProgramStatus.ACTIVE:
        raise DomainError(409, "program_not_active", "El programa no está activo")

    # Validación de modo y cálculo ANTES de tocar el saldo: o se aplica
    # completo o no se registra nada (§7.6).
    units = _earn_units(program, quantity=quantity, amount=amount)

    # Vencidos pendientes primero (bajo bloqueo): lo que caducó no se
    # acumula encima ni cuenta para el saldo que verá el cliente (§7.7).
    expire_due_stamps(session, membership, program)

    transaction = LoyaltyTransaction(
        merchant_id=membership.merchant_id,
        program_id=membership.program_id,
        membership_id=membership.id,
        transaction_type=TransactionType.EARN,
        quantity=units,
        idempotency_key=idempotency_key,
        created_by_user_id=actor_user_id,
        reason=reason,
        # Caducidad solo en modo sellos (§7.7): el campo de la regla se
        # llama `stamps_expire_days` y los puntos no caducan. Los lotes
        # emitidos sin regla nunca caducan (decisión de compra #6).
        expires_at=stamp_expiry_after(program.stamps_expire_days)
        if program.stamps_expire_days and program.program_type == ProgramType.STAMPS
        else None,
    )
    session.add(transaction)
    membership.stamps += units
    membership.version += 1
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        # Otra petición concurrente aplicó la misma clave: devolver la suya.
        concurrent = _existing_by_key(
            session, idempotency_key, merchant_id=merchant_id, membership_id=membership_id
        )
        if concurrent is None:
            raise DomainError(409, "duplicate_operation", "Operación ya registrada") from exc
        refreshed = session.get(Membership, concurrent.membership_id)
        if refreshed is None:
            raise DomainError(409, "duplicate_operation", "Operación ya registrada") from exc
        return OperationResult(concurrent, refreshed, already_applied=True)
    return OperationResult(transaction, membership)


def redeem(
    session: Session,
    membership_id: uuid.UUID,
    merchant_id: uuid.UUID,
    reward: ProgramReward,
    *,
    idempotency_key: str,
    actor_user_id: uuid.UUID | None,
) -> OperationResult:
    """Canje transaccional (§7.4): saldo suficiente, sin doble gasto, auditado."""
    existing = _existing_by_key(
        session, idempotency_key, merchant_id=merchant_id, membership_id=membership_id
    )
    if existing is not None:
        membership = session.get(Membership, existing.membership_id)
        if membership is None:
            raise DomainError(409, "duplicate_operation", "Operación ya registrada")
        return OperationResult(existing, membership, already_applied=True)

    membership = _load_membership_for_update(session, membership_id)
    program = _active_program(session, membership)
    if program.status != ProgramStatus.ACTIVE:
        raise DomainError(409, "program_not_active", "El programa no está activo")
    if not reward.is_active:
        raise DomainError(409, "reward_not_available", "Esta recompensa no está disponible")
    if reward.program_id != membership.program_id:
        raise DomainError(409, "reward_not_available", "Esta recompensa no pertenece al programa")

    # Primero se aplican los vencidos: no se puede canjear con sellos
    # caducados (§7.7). El saldo se reevalúa con el ledger al día.
    expire_due_stamps(session, membership, program)
    if membership.stamps < reward.stamps_required:
        raise DomainError(
            409,
            "insufficient_stamps",
            f"Faltan sellos: tienes {membership.stamps} y se necesitan {reward.stamps_required}",
        )

    transaction = LoyaltyTransaction(
        merchant_id=membership.merchant_id,
        program_id=membership.program_id,
        membership_id=membership.id,
        transaction_type=TransactionType.REDEEM,
        quantity=-reward.stamps_required,
        reward_id=reward.id,
        idempotency_key=idempotency_key,
        created_by_user_id=actor_user_id,
    )
    session.add(transaction)
    membership.stamps -= reward.stamps_required
    membership.version += 1
    session.flush()
    session.add(
        RewardRedemption(
            merchant_id=membership.merchant_id,
            membership_id=membership.id,
            reward_id=reward.id,
            transaction_id=transaction.id,
            redeemed_by_user_id=actor_user_id,
        )
    )
    session.flush()
    return OperationResult(transaction, membership)


def adjust(
    session: Session,
    membership_id: uuid.UUID,
    delta: int,
    *,
    reason: str,
    actor_user_id: uuid.UUID,
) -> OperationResult:
    """Ajuste manual con motivo (§7.3): solo roles autorizados, siempre trazado."""
    if delta == 0 or abs(delta) > 50:
        raise DomainError(422, "invalid_quantity", "Ajuste no válido")
    membership = _load_membership_for_update(session, membership_id)
    # Vencidos aplicados antes de evaluar el saldo del ajuste (§7.7).
    expire_due_stamps(session, membership, _active_program(session, membership))
    if membership.stamps + delta < 0:
        raise DomainError(409, "insufficient_stamps", "El ajuste dejaría la tarjeta en negativo")

    transaction = LoyaltyTransaction(
        merchant_id=membership.merchant_id,
        program_id=membership.program_id,
        membership_id=membership.id,
        transaction_type=TransactionType.ADJUSTMENT,
        quantity=delta,
        idempotency_key=f"adjust:{membership.id}:{uuid.uuid4().hex}",
        created_by_user_id=actor_user_id,
        reason=reason,
    )
    session.add(transaction)
    membership.stamps += delta
    membership.version += 1
    session.flush()
    return OperationResult(transaction, membership)


def list_transactions(session: Session, membership_id: uuid.UUID) -> list[LoyaltyTransaction]:
    rows = session.scalars(
        select(LoyaltyTransaction)
        .where(LoyaltyTransaction.membership_id == membership_id)
        .order_by(LoyaltyTransaction.created_at.desc())
    ).all()
    return list(rows)


def reconcile_stamps(session: Session, membership: Membership) -> int:
    """Sellos derivados del ledger: debe coincidir con la caché (§7.3)."""
    total = 0
    for transaction in list_transactions(session, membership.id):
        total += transaction.quantity
    return total


OperationKind = Literal["earn", "redeem", "adjust"]
