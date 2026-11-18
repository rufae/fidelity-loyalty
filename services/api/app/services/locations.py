"""Tiendas de un comercio (§11.3) con límites por plan contratado.

El plan (`domain/plans.py`) limita la **estructura**: tiendas dadas de alta y
programas en vivo simultáneos. Nunca limita clientes ni operaciones: el éxito
del comercio no se castiga.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import plan_limit_reached
from app.domain.plans import Plan
from app.domain.plans import get as get_plan
from app.domain.roles import MerchantRole as MerchantUserRole
from app.domain.roles import UserStatus as MerchantUserStatus
from app.models.loyalty import LoyaltyProgram, ProgramStatus
from app.models.merchant import Merchant, MerchantLocation
from app.models.user import MerchantUser

ACTIVE = "active"
INACTIVE = "inactive"


def list_locations(session: Session, merchant_id: uuid.UUID) -> list[MerchantLocation]:
    """Todas las tiendas del comercio, la activa primero."""
    rows = session.scalars(
        select(MerchantLocation)
        .where(MerchantLocation.merchant_id == merchant_id)
        .order_by(MerchantLocation.status, MerchantLocation.created_at)
    ).all()
    return list(rows)


def create_location(
    session: Session, merchant: Merchant, name: str, address: str | None
) -> MerchantLocation:
    """Alta de tienda; respeta el límite del plan (§3.3: nada oculto)."""
    plan = get_plan(merchant.plan)
    current = session.scalar(
        select(func.count(MerchantLocation.id)).where(
            MerchantLocation.merchant_id == merchant.id,
            MerchantLocation.status == ACTIVE,
        )
    )
    if current is not None and int(current) >= plan.max_locations:
        raise plan_limit_reached("locations", plan.max_locations)
    location = MerchantLocation(merchant_id=merchant.id, name=name, address=address, status=ACTIVE)
    session.add(location)
    session.flush()
    return location


def set_location_status(
    session: Session, merchant: Merchant, location: MerchantLocation, status: str
) -> MerchantLocation:
    """Activa/desactiva una tienda (no se borra: queda en el historial).

    Reactivar también respeta el plan: una tienda activa ocupa un hueco,
    igual que al darla de alta (§3.3: nada oculto).
    """
    if status == ACTIVE and location.status != ACTIVE:
        plan = get_plan(merchant.plan)
        current = session.scalar(
            select(func.count(MerchantLocation.id)).where(
                MerchantLocation.merchant_id == merchant.id,
                MerchantLocation.status == ACTIVE,
            )
        )
        if current is not None and int(current) >= plan.max_locations:
            raise plan_limit_reached("locations", plan.max_locations)
    location.status = status
    session.flush()
    return location


def count_active_programs(session: Session, merchant_id: uuid.UUID) -> int:
    """Programas de fidelización **en vivo** del comercio."""
    count = session.scalar(
        select(func.count(LoyaltyProgram.id)).where(
            LoyaltyProgram.merchant_id == merchant_id,
            LoyaltyProgram.status == ProgramStatus.ACTIVE,
        )
    )
    return int(count or 0)


def ensure_program_slot(session: Session, merchant_id: uuid.UUID, *, going_active: int = 1) -> None:
    """Comprueba que hay hueco para `going_active` programas más en vivo.

    Se llama al publicar (o reactivar desde pausa): los borradores son gratis,
    el límite es de programas simultáneamente activos.
    """
    merchant = session.get(Merchant, merchant_id)
    if merchant is None:
        return
    plan: Plan = get_plan(merchant.plan)
    active = count_active_programs(session, merchant_id)
    if active + going_active > plan.max_active_programs:
        raise plan_limit_reached("programs", plan.max_active_programs)


def plan_usage(session: Session, merchant: Merchant) -> dict[str, object]:
    """Uso real del plan para la interfaz del comercio (cifras de la BD)."""
    plan = get_plan(merchant.plan)
    locations = session.scalar(
        select(func.count(MerchantLocation.id)).where(
            MerchantLocation.merchant_id == merchant.id,
            MerchantLocation.status == ACTIVE,
        )
    )
    staff = session.scalar(
        select(func.count(MerchantUser.id)).where(
            MerchantUser.merchant_id == merchant.id,
            MerchantUser.status == MerchantUserStatus.ACTIVE.value,
            MerchantUser.role != MerchantUserRole.OWNER.value,
        )
    )
    return {
        "plan": plan.code,
        "plan_name": plan.name,
        "max_locations": plan.max_locations,
        "locations": int(locations or 0),
        "max_active_programs": plan.max_active_programs,
        "active_programs": count_active_programs(session, merchant.id),
        "max_staff": plan.max_staff,
        "staff": int(staff or 0),
    }
