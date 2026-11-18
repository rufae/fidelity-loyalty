"""Caducidad perezosa de sellos (decisión de compra #6, §7.3 y §7.7).

La regla es **opcional** y por programa (`stamps_expire_days`). Cada `earn`
fija su `expires_at`; cuando el lote vence, aquí se emite un movimiento
`expiry` negativo y auditable. El `earn` histórico nunca se edita ni borra
(§7.3): el saldo sigue derivándose del ledger completo.

El vencimiento es **perezoso**: se aplica antes de cada operación y al
serializar las fichas, de modo que el saldo mostrado y el que se usa para
canjar coinciden con el ledger. Es idempotente por construcción — al emitir
el movimiento, esos lotes quedan a cero en la simulación posterior — y la
clave única cubre carreras entre peticiones concurrentes.

Selección FIFO: los movimientos negativos (canje, ajuste, expiry) consumen
los lotes más antiguos primero, que son también los primeros en vencer.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ledger import LoyaltyTransaction, TransactionType
from app.models.loyalty import LoyaltyProgram, ProgramType
from app.models.members import Membership
from app.models.user import utcnow


def _as_utc(value: datetime) -> datetime:
    """SQLite devuelve fechas sin zona: se interpretan como UTC (§11.19)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@dataclass
class _Lot:
    """Saldo restante de un lote de sellos y su fecha de caducidad."""

    remaining: int
    expires_at: datetime | None


def due_stamps(session: Session, membership: Membership) -> tuple[int, datetime | None]:
    """Simula el ledger FIFO y devuelve `(sellos vencidos, corte más reciente)`.

    Recorre los movimientos en orden temporal: los `earn` abren lotes (con
    su fecha de caducidad si la regla la fijó) y los negativos consumen los
    lotes más antiguos. Después suma el saldo restante de los lotes cuya
    fecha ya pasó. Solo hay que llamarlo cuando el programa define la regla.
    """
    rows = session.scalars(
        select(LoyaltyTransaction)
        .where(LoyaltyTransaction.membership_id == membership.id)
        .order_by(LoyaltyTransaction.created_at.asc(), LoyaltyTransaction.id.asc())
    ).all()

    now = utcnow()
    lots: list[_Lot] = []
    for tx in rows:
        if tx.quantity > 0:
            expires = tx.expires_at if tx.transaction_type == TransactionType.EARN else None
            lots.append(_Lot(remaining=tx.quantity, expires_at=expires))
            continue
        pending = -tx.quantity
        for lot in lots:
            if pending <= 0:
                break
            if lot.remaining <= 0:
                continue
            take = min(lot.remaining, pending)
            lot.remaining -= take
            pending -= take

    expired = 0
    cutoff: datetime | None = None
    for lot in lots:
        if lot.remaining <= 0 or lot.expires_at is None:
            continue
        expires_utc = _as_utc(lot.expires_at)
        if expires_utc <= now:
            expired += lot.remaining
            if cutoff is None or expires_utc > cutoff:
                cutoff = expires_utc
    return expired, cutoff


def expire_due_stamps(
    session: Session,
    membership: Membership,
    program: LoyaltyProgram | None = None,
) -> int:
    """Emite el movimiento `expiry` de los sellos vencidos; devuelve cuántos.

    - Programa sin regla → coste cero (ni siquiera consulta el ledger).
    - Segura bajo el bloqueo de la membresía (operaciones) y en lecturas:
      usa un savepoint, de modo que una carrera con otra petición que ya
      haya emitido el movimiento no rompe la transacción en curso.
    """
    if program is None:
        program = session.get(LoyaltyProgram, membership.program_id)
    if program is None or program.stamps_expire_days is None:
        return 0
    if program.program_type == ProgramType.POINTS:
        # La caducidad es de sellos (`stamps_expire_days`, §7.7): los
        # puntos por importe no vencen.
        return 0

    expired, cutoff = due_stamps(session, membership)
    if expired <= 0 or cutoff is None:
        return 0

    transaction = LoyaltyTransaction(
        merchant_id=membership.merchant_id,
        program_id=membership.program_id,
        membership_id=membership.id,
        transaction_type=TransactionType.EXPIRY,
        quantity=-expired,
        idempotency_key=f"expiry:{membership.id}:{int(cutoff.timestamp())}",
        source="system",
        reason="Sellos caducados según la regla del programa",
    )
    try:
        with session.begin_nested():
            session.add(transaction)
            membership.stamps -= expired
            membership.version += 1
            session.flush()
    except IntegrityError:
        # Otra petición ya emitió este vencimiento: no duplicar (§16.4).
        return 0
    return expired


def stamp_expiry_after(days: int, *, now: datetime | None = None) -> datetime:
    """Fecha de caducidad de un lote nuevo según la regla vigente."""
    base = now or utcnow()
    return base + timedelta(days=days)
