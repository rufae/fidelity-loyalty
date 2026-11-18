"""Operaciones de fidelización sobre una membresía (§12.7).

Permisos:
- `earn`/`redeem`: roles operativos (`owner`, `admin`, `staff`).
- `adjust`: solo administración del comercio (§7.3: ajustes con motivo).

Idempotencia: la clave llega en el cuerpo (`idempotency_key`); una repetición
 devuelve el mismo movimiento sin aplicar el efecto dos veces (§16.4).
"""

import io
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import DbSession, merchant_access
from app.core.config import Settings, get_settings
from app.core.urls import absolute_url, resolve_public_base
from app.domain.roles import MERCHANT_ADMIN_ROLES, MERCHANT_OPERATOR_ROLES
from app.models.members import Membership
from app.schemas.members import MembershipOut
from app.services import ledger as ledger_service
from app.services import members as members_service
from app.services import wallet as wallet_service
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchants/{merchant_id}/memberships", tags=["operaciones"])

merchant_operator = merchant_access(MERCHANT_OPERATOR_ROLES)
merchant_admin = merchant_access(MERCHANT_ADMIN_ROLES)

OperatorDep = Annotated[object, Depends(merchant_operator)]
AdminDep = Annotated[object, Depends(merchant_admin)]


class EarnRequest(BaseModel):
    #: Modo sellos: unidades por visita (1–20). Omitido = 1.
    quantity: int | None = Field(default=None, ge=1, le=20)
    #: Modo puntos (§7.6): importe de la venta en euros, hasta dos
    #: decimales. Los puntos los calcula el backend con la regla del
    #: programa: el navegador jamás envía la cantidad a otorgar.
    amount: Decimal | None = Field(default=None, ge=Decimal("0.01"), le=Decimal("10000"))
    idempotency_key: str = Field(min_length=8, max_length=120)
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("amount")
    @classmethod
    def _two_decimals(cls, value: Decimal | None) -> Decimal | None:
        """Importes con máximo dos decimales: nada de fracciones raras."""
        if value is None:
            return None
        if value != value.quantize(Decimal("0.01")):
            raise ValueError("máximo dos decimales")
        return value


class RedeemRequest(BaseModel):
    reward_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=120)


class AdjustRequest(BaseModel):
    delta: int = Field(ge=-50, le=50)
    reason: str = Field(min_length=3, max_length=255)


class OperationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: uuid.UUID
    membership_id: uuid.UUID
    transaction_type: str
    quantity: int
    stamps: int
    already_applied: bool = False


def reward_program_merchant(session: DbSession, reward: object) -> uuid.UUID:
    """Merchant del que administra una recompensa (para no canjear ajenas)."""
    from app.models.loyalty import LoyaltyProgram

    program = session.get(LoyaltyProgram, reward.program_id)  # type: ignore[attr-defined]
    assert program is not None
    return program.merchant_id


def _scoped_membership(
    session: DbSession, merchant_id: uuid.UUID, membership_id: uuid.UUID
) -> None:
    """El ámbito de comercio se comprueba en la API: un ID ajeno es 404 (§8.2)."""
    from app.domain.errors import not_found

    membership = session.get(Membership, membership_id)
    if membership is None or str(membership.merchant_id) != str(merchant_id):
        raise not_found("Membresía")


def _out(result: ledger_service.OperationResult) -> OperationOut:
    return OperationOut(
        transaction_id=result.transaction.id,
        membership_id=result.membership.id,
        transaction_type=result.transaction.transaction_type,
        quantity=result.transaction.quantity,
        stamps=result.membership.stamps,
        already_applied=result.already_applied,
    )


def _sync_wallets(session: Session, membership: Membership, settings: Settings) -> None:
    """Sincroniza los pases tras una operación confirmada (§6.1, §15).

    Se ejecuta **después** del commit del ledger y con protección total: un
    fallo del proveedor deja el trabajo visible para reintentar, pero jamás
    afecta al movimiento ya registrado.
    """
    try:
        wallet_service.update_passes_after_operation(session, membership, settings)
        session.commit()
    except Exception:  # noqa: BLE001 — defensa en profundidad de §6.1
        logger.exception("wallet: fallo sincronizando tras operación confirmada")
        session.rollback()


@router.get("/{membership_id}", response_model=MembershipOut)
def get_membership(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    session: DbSession,
    context: OperatorDep,  # noqa: ARG001
) -> MembershipOut:
    membership = session.get(Membership, membership_id)
    # El filtro por comercio evita leer membresías ajenas por ID (§8.2).
    if membership is None or str(membership.merchant_id) != str(merchant_id):
        from app.domain.errors import not_found

        raise not_found("Membresía")
    return MembershipOut.model_validate(membership)


@router.post("/{membership_id}/earn", response_model=OperationOut, status_code=201)
def earn(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: EarnRequest,
    session: DbSession,
    context: OperatorDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> OperationOut:
    _scoped_membership(session, merchant_id, membership_id)
    result = ledger_service.earn(
        session,
        membership_id,
        merchant_id,
        quantity=data.quantity,
        amount=data.amount,
        idempotency_key=data.idempotency_key,
        actor_user_id=context.user.id,  # type: ignore[attr-defined]
        reason=data.reason,
    )
    if not result.already_applied:
        audit_meta: dict[str, str] = {}
        if data.reason:
            audit_meta["reason"] = data.reason
        if data.amount is not None:
            # Importe de la venta registrado en auditoría (§8.4): sin PII.
            audit_meta["amount_eur"] = str(data.amount)
        record_audit(
            session,
            action="loyalty.earn",
            entity_type="membership",
            actor_id=context.user.id,  # type: ignore[attr-defined]
            merchant_id=merchant_id,
            entity_id=str(membership_id),
            metadata=audit_meta or None,
        )
        # El sello se confirma en base de datos ANTES de tocar Wallet: un
        # fallo del proveedor nunca puede deshacer la operación del ledger
        # (§6.1, regla irrenunciable).
        session.commit()
        _sync_wallets(session, result.membership, settings)
    return _out(result)


@router.post("/{membership_id}/redeem", response_model=OperationOut, status_code=201)
def redeem(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: RedeemRequest,
    session: DbSession,
    context: OperatorDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> OperationOut:
    from app.domain.errors import not_found
    from app.models.loyalty import ProgramReward

    _scoped_membership(session, merchant_id, membership_id)
    reward = session.get(ProgramReward, data.reward_id)
    if reward is None or str(reward_program_merchant(session, reward)) != str(merchant_id):
        raise not_found("Recompensa")
    result = ledger_service.redeem(
        session,
        membership_id,
        merchant_id,
        reward,
        idempotency_key=data.idempotency_key,
        actor_user_id=context.user.id,  # type: ignore[attr-defined]
    )
    if not result.already_applied:
        record_audit(
            session,
            action="loyalty.redeem",
            entity_type="membership",
            actor_id=context.user.id,  # type: ignore[attr-defined]
            merchant_id=merchant_id,
            entity_id=str(membership_id),
        )
        # Igual que en `earn`: el canje se confirma antes de sincronizar
        # Wallet; un fallo del proveedor no revierte el movimiento (§6.1).
        session.commit()
        _sync_wallets(session, result.membership, settings)
    return _out(result)


@router.post("/{membership_id}/adjust", response_model=OperationOut, status_code=201)
def adjust(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: AdjustRequest,
    session: DbSession,
    context: AdminDep,
) -> OperationOut:
    _scoped_membership(session, merchant_id, membership_id)
    result = ledger_service.adjust(
        session,
        membership_id,
        data.delta,
        reason=data.reason,
        actor_user_id=context.user.id,  # type: ignore[attr-defined]
    )
    record_audit(
        session,
        action="loyalty.adjust",
        entity_type="membership",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(membership_id),
        metadata={"reason": data.reason},
    )
    session.commit()
    return _out(result)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_type: str
    quantity: int
    reward_id: uuid.UUID | None = None
    reason: str | None = None
    created_at: datetime


class LookupRequest(BaseModel):
    """El personal introduce o escanea el código de la tarjeta (§13.5)."""

    token: str = Field(min_length=16, max_length=64)


@router.post("/lookup", response_model=MembershipOut)
def lookup_by_token(
    merchant_id: uuid.UUID,
    data: LookupRequest,
    session: DbSession,
    context: OperatorDep,  # noqa: ARG001
) -> MembershipOut:
    """Resuelve el código público de una tarjeta **dentro de este comercio**.

    Un token de otro comercio responde 404 idéntico al inexistente (§8.2): el
    QR no es una credencial ni permite atravesar el aislamiento.
    """
    from app.domain.errors import not_found

    membership = session.scalar(select(Membership).where(Membership.public_token == data.token))
    if membership is None or str(membership.merchant_id) != str(merchant_id):
        raise not_found("Membresía")
    return members_service.to_out(session, merchant_id, membership)


@router.get("/{membership_id}/qr")
def membership_qr(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    request: Request,
    session: DbSession,
    context: OperatorDep,  # noqa: ARG001
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """QR (SVG) de la tarjeta del cliente: para imprimir o mostrar (§14.1).

    El contenido es la **URL absoluta** de la tarjeta del cliente (con su
    token opaco dentro): al escanearla se abre la tarjeta y el personal puede
    pegar la URL en el buscador de operaciones.
    """
    _scoped_membership(session, merchant_id, membership_id)
    membership = session.get(Membership, membership_id)
    assert membership is not None
    import segno

    base = resolve_public_base(request, settings)
    content = absolute_url(f"/card/{membership.public_token}", base)
    qr = segno.make(content, error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=8, border=2)
    return Response(
        content=buffer.getvalue(),
        media_type="image/svg+xml",
        headers={"X-QR-Content": content},
    )


@router.get("/{membership_id}/transactions", response_model=list[TransactionOut])
def list_transactions(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    session: DbSession,
    context: OperatorDep,  # noqa: ARG001
) -> list[TransactionOut]:
    from app.domain.errors import not_found

    membership = session.get(Membership, membership_id)
    if membership is None or str(membership.merchant_id) != str(merchant_id):
        raise not_found("Membresía")
    rows = ledger_service.list_transactions(session, membership_id)
    return [TransactionOut.model_validate(t) for t in rows]
