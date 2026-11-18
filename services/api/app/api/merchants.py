"""Gestión del comercio por su propio equipo (AGENTS.md §12.3).

El `merchant_id` del camino identifica el recurso; el permiso sale de la
sesión (`merchant_access`), nunca del cliente (§8.2).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import ContextDep, DbSession, merchant_access
from app.domain.errors import DomainError
from app.domain.roles import (
    MERCHANT_ADMIN_ROLES,
    MERCHANT_READ_ROLES,
    MerchantRole,
    UserStatus,
    role_rank,
)
from app.models.merchant import MerchantLocation
from app.models.user import MerchantUser
from app.schemas.auth import SessionUser
from app.schemas.merchant import (
    LocationCreate,
    LocationOut,
    LocationStatusUpdate,
    MerchantOut,
    MerchantUpdate,
    MerchantUserCreate,
    MerchantUserOut,
    MerchantUserUpdate,
    PlanUsageOut,
)
from app.services import locations as locations_service
from app.services import merchants as merchants_service
from app.services.audit import record_audit
from app.services.auth import SessionContext

router = APIRouter(prefix="/merchants", tags=["comercios"])

MerchantReadDep = Annotated[SessionContext, Depends(merchant_access(MERCHANT_READ_ROLES))]
MerchantAdminDep = Annotated[SessionContext, Depends(merchant_access(MERCHANT_ADMIN_ROLES))]


def _user_out(membership: object, user: object) -> MerchantUserOut:
    return MerchantUserOut(
        id=membership.id,  # type: ignore[attr-defined]
        user_id=user.id,  # type: ignore[attr-defined]
        email=user.email,  # type: ignore[attr-defined]
        display_name=user.display_name,  # type: ignore[attr-defined]
        role=membership.role,  # type: ignore[attr-defined]
        status=membership.status,  # type: ignore[attr-defined]
        created_at=membership.created_at,  # type: ignore[attr-defined]
    )


@router.get("", response_model=list[MerchantOut])
def my_merchants(session: DbSession, context: ContextDep) -> list[MerchantOut]:
    """Comercios de la sesión (los suyos, o todos si administra la plataforma)."""
    if context.is_platform_admin:
        merchants = merchants_service.list_platform_merchants(session)
    else:
        merchants = merchants_service.list_merchants(session, list(context.merchant_roles))
    return [MerchantOut.model_validate(m) for m in merchants]


@router.get("/{merchant_id}", response_model=MerchantOut)
def get_merchant(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantReadDep,  # noqa: ARG001 - la dependencia es el permiso
) -> MerchantOut:
    merchant = merchants_service.get_merchant(session, merchant_id)
    return MerchantOut.model_validate(merchant)


@router.patch("/{merchant_id}", response_model=MerchantOut)
def update_merchant(
    merchant_id: uuid.UUID,
    data: MerchantUpdate,
    session: DbSession,
    context: MerchantAdminDep,
) -> MerchantOut:
    merchant = merchants_service.get_merchant(session, merchant_id)
    merchant = merchants_service.update_merchant(session, merchant, data)
    record_audit(
        session,
        action="merchant.updated",
        entity_type="merchant",
        actor_id=context.user.id,
        merchant_id=merchant.id,
        entity_id=str(merchant.id),
    )
    session.commit()
    return MerchantOut.model_validate(merchant)


@router.get("/{merchant_id}/users", response_model=list[MerchantUserOut])
def list_users(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantAdminDep,  # noqa: ARG001
) -> list[MerchantUserOut]:
    rows = merchants_service.list_merchant_users(session, merchant_id)
    return [_user_out(membership, user) for membership, user in rows]


@router.post("/{merchant_id}/users", response_model=MerchantUserOut, status_code=201)
def add_user(
    merchant_id: uuid.UUID,
    data: MerchantUserCreate,
    session: DbSession,
    context: MerchantAdminDep,
) -> MerchantUserOut:
    actor_role = context.merchant_role(merchant_id)
    # Un `admin` no puede incorporar a otro `owner` (escalada de privilegios).
    if actor_role == MerchantRole.ADMIN and data.role == MerchantRole.OWNER:
        raise DomainError(403, "merchant_access_denied", "Permiso insuficiente")
    merchant = merchants_service.get_merchant(session, merchant_id)
    membership, user = merchants_service.add_merchant_user(session, merchant, data)
    record_audit(
        session,
        action="merchant.user.added",
        entity_type="merchant_user",
        actor_id=context.user.id,
        merchant_id=merchant_id,
        entity_id=str(user.id),
        metadata={"role": data.role.value},
    )
    session.commit()
    return _user_out(membership, user)


@router.patch("/{merchant_id}/users/{user_id}", response_model=MerchantUserOut)
def update_user(
    merchant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MerchantUserUpdate,
    session: DbSession,
    context: MerchantAdminDep,
) -> MerchantUserOut:
    actor_role = context.merchant_role(merchant_id)
    if actor_role == MerchantRole.ADMIN and data.role == MerchantRole.OWNER:
        raise DomainError(403, "merchant_access_denied", "Permiso insuficiente")
    if data.status is not None and data.status not in {s.value for s in UserStatus}:
        raise DomainError(400, "invalid_status", "Estado no válido")
    # Jerarquía de roles (§8.1): nadie modifica a un rol de rango superior al
    # suyo. Sin esto, un `admin` podría degradar o deshabilitar a un `owner`
    # y desplazar al propietario del comercio.
    target = session.scalar(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_id, MerchantUser.user_id == user_id
        )
    )
    if target is not None and actor_role is not None:
        try:
            target_role = MerchantRole(target.role)
        except ValueError:
            target_role = None
        if target_role is not None and role_rank(actor_role) < role_rank(target_role):
            raise DomainError(403, "merchant_access_denied", "Permiso insuficiente")
    merchants_service.remove_owner_guard(session, merchant_id, user_id)
    membership, user = merchants_service.update_merchant_user(session, merchant_id, user_id, data)
    record_audit(
        session,
        action="merchant.user.updated",
        entity_type="merchant_user",
        actor_id=context.user.id,
        merchant_id=merchant_id,
        entity_id=str(user.id),
        metadata={"role": membership.role},
    )
    session.commit()
    return _user_out(membership, user)


@router.get("/{merchant_id}/session-user", response_model=SessionUser)
def session_user(merchant_id: uuid.UUID, context: MerchantReadDep) -> SessionUser:
    """Comprueba que la sesión ve este comercio; la interfaz lo usa como guardia."""
    return SessionUser.model_validate(context.user)


@router.get("/{merchant_id}/locations", response_model=list[LocationOut])
def list_locations(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantReadDep,  # noqa: ARG001
) -> list[LocationOut]:
    """Tiendas del comercio (§11.3). Lectura para todo el equipo."""
    return [
        LocationOut.model_validate(row)
        for row in locations_service.list_locations(session, merchant_id)
    ]


@router.post("/{merchant_id}/locations", response_model=LocationOut, status_code=201)
def create_location(
    merchant_id: uuid.UUID,
    data: LocationCreate,
    session: DbSession,
    context: MerchantAdminDep,
) -> LocationOut:
    """Alta de tienda; el límite lo pone el plan contratado (§3.3)."""
    merchant = merchants_service.get_merchant(session, merchant_id)
    location = locations_service.create_location(session, merchant, data.name, data.address)
    record_audit(
        session,
        action="merchant.location_created",
        entity_type="merchant_location",
        actor_id=context.user.id,
        merchant_id=merchant_id,
        entity_id=str(location.id),
        metadata={"name": location.name},
    )
    session.commit()
    return LocationOut.model_validate(location)


@router.patch("/{merchant_id}/locations/{location_id}", response_model=LocationOut)
def update_location(
    merchant_id: uuid.UUID,
    location_id: uuid.UUID,
    data: LocationStatusUpdate,
    session: DbSession,
    context: MerchantAdminDep,
) -> LocationOut:
    """Activa o desactiva una tienda (no se borra: queda en el historial)."""
    location = session.get(MerchantLocation, location_id)
    if location is None or location.merchant_id != merchant_id:
        # 404 idéntico a inexistente: una tienda ajena no se enumera (§8.2).
        raise DomainError(404, "location_not_found", "Tienda no encontrada")
    merchant = merchants_service.get_merchant(session, merchant_id)
    location = locations_service.set_location_status(session, merchant, location, data.status)
    record_audit(
        session,
        action="merchant.location_status_changed",
        entity_type="merchant_location",
        actor_id=context.user.id,
        merchant_id=merchant_id,
        entity_id=str(location.id),
        metadata={"status": location.status},
    )
    session.commit()
    return LocationOut.model_validate(location)


@router.get("/{merchant_id}/plan", response_model=PlanUsageOut)
def plan_usage(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: MerchantReadDep,  # noqa: ARG001
) -> PlanUsageOut:
    """Plan contratado y su uso real (cifras de la base de datos, §13.2)."""
    merchant = merchants_service.get_merchant(session, merchant_id)
    return PlanUsageOut.model_validate(locations_service.plan_usage(session, merchant))
