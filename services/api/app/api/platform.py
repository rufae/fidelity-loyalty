"""Administración global de la plataforma (AGENTS.md §12.2, §8.1).

Solo para `platform_owner`/`platform_admin`. Aquí se dan de alta los comercios
que contratan el servicio; la gestión diaria del comercio vive en
`app/api/merchants.py`.
"""

import uuid

from fastapi import APIRouter

from app.api.deps import DbSession, PlatformAdminDep
from app.domain.errors import user_exists
from app.domain.roles import MerchantStatus, PlatformRole
from app.schemas.merchant import MerchantCreate, MerchantOut, MerchantUpdate
from app.services import merchants as merchants_service
from app.services.audit import record_audit
from app.services.auth import find_user_by_email

router = APIRouter(prefix="/platform", tags=["plataforma"])


@router.get("/merchants", response_model=list[MerchantOut])
def list_merchants(session: DbSession, context: PlatformAdminDep) -> list[MerchantOut]:  # noqa: ARG001
    """Todos los comercios de la plataforma (solo administración global)."""
    merchants = merchants_service.list_platform_merchants(session)
    return [MerchantOut.model_validate(m) for m in merchants]


@router.post("/merchants", response_model=MerchantOut, status_code=201)
def create_merchant(
    data: MerchantCreate, session: DbSession, context: PlatformAdminDep
) -> MerchantOut:
    """Alta de comercio con su propietario; el slug se genera y desambigua solo."""
    if find_user_by_email(session, str(data.owner_email)) is not None:
        # Un email ya registrado debe incorporarse como owner en la FASE 2.x:
        # por ahora no se silencia el conflicto con un usuario sin comercio.
        raise user_exists()
    merchant, owner = merchants_service.create_merchant(session, data)
    record_audit(
        session,
        action="merchant.created",
        entity_type="merchant",
        actor_id=context.user.id,
        merchant_id=merchant.id,
        entity_id=str(merchant.id),
        metadata={"fields": ["name", "slug", "owner"]},
    )
    session.commit()
    return MerchantOut.model_validate(merchant)


@router.get("/merchants/{merchant_id}", response_model=MerchantOut)
def get_merchant(
    merchant_id: uuid.UUID, session: DbSession, context: PlatformAdminDep
) -> MerchantOut:
    merchant = merchants_service.get_merchant(session, merchant_id)
    return MerchantOut.model_validate(merchant)


@router.patch("/merchants/{merchant_id}", response_model=MerchantOut)
def update_merchant(
    merchant_id: uuid.UUID,
    data: MerchantUpdate,
    session: DbSession,
    context: PlatformAdminDep,
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


@router.post("/merchants/{merchant_id}/suspend", response_model=MerchantOut)
def suspend_merchant(
    merchant_id: uuid.UUID, session: DbSession, context: PlatformAdminDep
) -> MerchantOut:
    merchant = merchants_service.get_merchant(session, merchant_id)
    previous = merchant.status
    merchant = merchants_service.set_merchant_status(session, merchant, MerchantStatus.SUSPENDED)
    record_audit(
        session,
        action="merchant.suspended",
        entity_type="merchant",
        actor_id=context.user.id,
        merchant_id=merchant.id,
        entity_id=str(merchant.id),
        metadata={"previous_status": previous, "new_status": merchant.status},
    )
    session.commit()
    return MerchantOut.model_validate(merchant)


@router.post("/merchants/{merchant_id}/activate", response_model=MerchantOut)
def activate_merchant(
    merchant_id: uuid.UUID, session: DbSession, context: PlatformAdminDep
) -> MerchantOut:
    merchant = merchants_service.get_merchant(session, merchant_id)
    previous = merchant.status
    merchant = merchants_service.set_merchant_status(session, merchant, MerchantStatus.ACTIVE)
    record_audit(
        session,
        action="merchant.activated",
        entity_type="merchant",
        actor_id=context.user.id,
        merchant_id=merchant.id,
        entity_id=str(merchant.id),
        metadata={"previous_status": previous, "new_status": merchant.status},
    )
    session.commit()
    return MerchantOut.model_validate(merchant)


@router.get("/roles", response_model=dict[str, str])
def roles_reference() -> dict[str, str]:
    """Referencia de roles para la interfaz (información pública, sin datos)."""
    return {
        "platform": ", ".join(role.value for role in PlatformRole),
        "merchant": "owner, admin, staff, viewer",
    }
