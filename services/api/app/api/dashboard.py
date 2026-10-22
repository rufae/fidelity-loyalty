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
from app.domain.roles import MERCHANT_ADMIN_ROLES
from app.services import dashboard as dashboard_service
from app.services import members as members_service

router = APIRouter(prefix="/merchants/{merchant_id}", tags=["analítica"])
admin = merchant_access(MERCHANT_ADMIN_ROLES)
AdminDep = Annotated[object, Depends(admin)]

PERIOD_DAYS: Mapping[str, int] = {"7": 7, "30": 30, "90": 90}


@router.get("/dashboard/summary")
def summary(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: AdminDep,  # noqa: ARG001
) -> Mapping[str, int]:
    """Indicadores reales del comercio (§13.2, §24)."""
    return dashboard_service.summary(session, merchant_id)


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
