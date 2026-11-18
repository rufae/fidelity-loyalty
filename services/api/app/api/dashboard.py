"""Endpoints de analítica y exportación del comercio (§12.9, §21.2).

Solo administración del comercio. La exportación sale en CSV con los datos
propios del comercio y sin tokens públicos (§21.2: minimización).
"""

import csv
import io
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import DbSession, merchant_access
from app.domain.roles import MERCHANT_ADMIN_ROLES, MERCHANT_OPERATOR_ROLES
from app.schemas.members import MembershipOut
from app.services import dashboard as dashboard_service
from app.services import members as members_service

router = APIRouter(prefix="/merchants/{merchant_id}", tags=["analítica"])
admin = merchant_access(MERCHANT_ADMIN_ROLES)
AdminDep = Annotated[object, Depends(admin)]
operator = merchant_access(MERCHANT_OPERATOR_ROLES)
OperatorDep = Annotated[object, Depends(operator)]

PERIOD_DAYS: Mapping[str, int] = {"7": 7, "30": 30, "90": 90}


@router.get("/dashboard/summary")
def summary(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> Mapping[str, int]:
    """Indicadores reales del comercio (§13.2, §24)."""
    return dashboard_service.summary(session, merchant_id)


@router.get("/dashboard/onboarding")
def onboarding(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> Mapping[str, bool]:
    """Primeros pasos del comercio para llegar al primer sello (§13.2).

    Pública: no. Autenticada: sí, con rol de administración del comercio
    (misma `AdminDep` que el resto del Resumen). Límite propio: sin
    endpoint rate limit propio (hereda el de sesión; solo lectura).
    Devuelve cuatro booleanos de progreso más `completed`: sin PII, sin
    identificadores y sin posibilidad de enumerar datos de otros
    comercios (§8.2). Idempotencia: no aplica (solo lectura, sin efectos
    secundarios).
    """
    return dashboard_service.onboarding_checklist(session, merchant_id)


@router.get("/dashboard/today")
def today(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> Mapping[str, object]:
    """Cierre de turno: altas, sellos y canjes de hoy (§13.2, §24.2).

    «Hoy» es el día de la **zona horaria del comercio** (el ledger guarda
    UTC). Cifras del día, no acumuladas, siempre desde la base de datos.
    """
    return dashboard_service.today_summary(session, merchant_id)


@router.get("/dashboard/loyalty")
def loyalty_series(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
    period: str = "30",
) -> Mapping[str, object]:
    """Serie diaria de operaciones del periodo indicado (7, 30 o 90 días)."""
    days = PERIOD_DAYS.get(period, 30)
    since = datetime.now(UTC) - timedelta(days=days)
    return {
        "period_days": days,
        "series": dashboard_service.transactions_series(session, merchant_id, since),
    }


@router.get("/export/transactions.csv")
def export_transactions(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> Response:
    """Exporta el libro de movimientos del comercio en CSV (§21.2).

    Columnas mínimas y trazables: fecha, tarjeta (token opaco, sin PII),
    programa, tipo, cantidad con signo y motivo del ajuste si lo hay. Nunca
    incluye datos personales del cliente: para eso está la exportación de
    miembros, y cada cosa para su gestión.
    """
    from sqlalchemy import select

    from app.models.ledger import LoyaltyTransaction
    from app.models.loyalty import LoyaltyProgram
    from app.models.members import Membership

    rows = session.execute(
        select(
            LoyaltyTransaction.created_at,
            Membership.public_token,
            LoyaltyProgram.name,
            LoyaltyTransaction.transaction_type,
            LoyaltyTransaction.quantity,
            LoyaltyTransaction.reason,
        )
        .join(Membership, LoyaltyTransaction.membership_id == Membership.id)
        .join(LoyaltyProgram, LoyaltyTransaction.program_id == LoyaltyProgram.id)
        .where(LoyaltyTransaction.merchant_id == merchant_id)
        .order_by(LoyaltyTransaction.created_at.desc())
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["fecha_utc", "tarjeta", "programa", "tipo", "cantidad", "motivo"])
    for created_at, token, program, ttype, quantity, reason in rows:
        writer.writerow(
            [
                created_at.isoformat() if created_at is not None else "",
                token,
                program,
                ttype,
                quantity,
                reason or "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transacciones.csv"},
    )


@router.get("/enrollments/today", response_model=list[MembershipOut])
def enrollments_today(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: OperatorDep,  # noqa: ARG001
) -> list[MembershipOut]:
    """Altas de hoy del comercio para el mostrador (mejora de compra #2).

    Rol operativo (el personal es quien da la bienvenida). La lista usa la
    salida enriquecida de membresías: nombre mínimo, programa, sellos y la
    insignia «Premio listo» si ya tocara. Sin datos de contacto.
    """
    day_start_utc, _local_date = dashboard_service._merchant_day_start_utc(session, merchant_id)
    rows = dashboard_service.recent_enrollments(session, merchant_id, day_start_utc)
    outs = members_service.to_outs(session, merchant_id, rows)
    # Identidad mínima para la bienvenida (§9.3): nombre y tarjeta, sin correo.
    for out in outs:
        out.member_email = None
    return outs


@router.get("/export/members.csv")
def export_members(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> Response:
    """Exporta los miembros del comercio en CSV (datos propios, §21.2)."""
    rows = members_service.list_members(session, merchant_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "display_name", "status", "created_at"])
    for member in rows:
        # Sin IDs internos ni tokens: solo lo necesario para gestionar el programa.
        writer.writerow(
            [member.email or "", member.display_name or "", member.status, member.created_at]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=miembros.csv"},
    )
