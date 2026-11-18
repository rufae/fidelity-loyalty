"""Servicio de comercios: alta, edición, suspensión y equipo (§12.2, §12.3).

Toda función recibe el `merchant_id` **y** exige verificarlo contra el contexto
de sesión en la capa de API (§8.2): aquí no se decide quién puede ver qué.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.errors import not_found, plan_limit_reached, user_exists
from app.domain.plans import get as get_plan
from app.domain.roles import MerchantRole, MerchantStatus, UserStatus
from app.models.merchant import Merchant, slugify
from app.models.user import MerchantUser, User
from app.schemas.auth import SessionUser
from app.schemas.merchant import (
    MerchantCreate,
    MerchantUpdate,
    MerchantUserCreate,
    MerchantUserUpdate,
)


def _unique_slug(session: Session, base: str) -> str:
    slug = slugify(base)
    candidate = slug
    suffix = 2
    while session.scalar(select(Merchant.id).where(Merchant.slug == candidate)) is not None:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def _find_user_or_create(session: Session, email: str, password: str, display_name: str) -> User:
    normalized = email.strip().lower()
    user = session.scalar(select(User).where(User.email == normalized))
    if user is not None:
        return user
    user = User(
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name,
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()
    return user


def create_merchant(session: Session, data: MerchantCreate) -> tuple[Merchant, User]:
    """Alta de comercio con su propietario. El slug se genera y se desambigua."""
    owner = _find_user_or_create(
        session, str(data.owner_email), data.owner_password, data.owner_display_name
    )
    merchant = Merchant(
        name=data.name.strip(),
        slug=_unique_slug(session, data.name),
        legal_name=data.legal_name,
        timezone=data.timezone,
        country_code=data.country_code.upper(),
        default_locale=data.default_locale,
        status=MerchantStatus.ACTIVE.value,
    )
    session.add(merchant)
    session.flush()
    session.add(
        MerchantUser(
            user_id=owner.id,
            merchant_id=merchant.id,
            role=MerchantRole.OWNER.value,
            status=UserStatus.ACTIVE.value,
        )
    )
    session.flush()
    return merchant, owner


def list_merchants(session: Session, merchant_ids: list[uuid.UUID]) -> list[Merchant]:
    if not merchant_ids:
        return []
    rows = session.scalars(select(Merchant).where(Merchant.id.in_(merchant_ids))).all()
    return sorted(rows, key=lambda m: m.name.lower())


def list_platform_merchants(session: Session) -> list[Merchant]:
    """Todos los comercios (solo la capa de API de plataforma debe llamarlo)."""
    rows = session.scalars(select(Merchant)).all()
    return sorted(rows, key=lambda m: m.name.lower())


def get_merchant(session: Session, merchant_id: uuid.UUID) -> Merchant:
    merchant = session.get(Merchant, merchant_id)
    if merchant is None:
        raise not_found("Comercio")
    return merchant


def update_merchant(session: Session, merchant: Merchant, data: MerchantUpdate) -> Merchant:
    if data.name is not None:
        merchant.name = data.name.strip()
    if data.legal_name is not None:
        merchant.legal_name = data.legal_name
    if data.timezone is not None:
        merchant.timezone = data.timezone
    session.flush()
    return merchant


def set_merchant_status(session: Session, merchant: Merchant, status: MerchantStatus) -> Merchant:
    merchant.status = status.value
    session.flush()
    return merchant


def list_merchant_users(
    session: Session, merchant_id: uuid.UUID
) -> list[tuple[MerchantUser, User]]:
    memberships = session.scalars(
        select(MerchantUser).where(MerchantUser.merchant_id == merchant_id)
    ).all()
    result: list[tuple[MerchantUser, User]] = []
    for membership in memberships:
        user = session.get(User, membership.user_id)
        if user is not None:
            result.append((membership, user))
    return sorted(result, key=lambda item: item[1].email)


def add_merchant_user(
    session: Session, merchant: Merchant, data: MerchantUserCreate
) -> tuple[MerchantUser, SessionUser]:
    """Alta de personal respetando el plan (empleado activo ocupa hueco)."""
    plan = get_plan(merchant.plan)
    normalized = str(data.email).strip().lower()
    existing = session.scalar(select(User).where(User.email == normalized))
    if existing is not None:
        already_member = session.scalar(
            select(MerchantUser).where(
                MerchantUser.user_id == existing.id, MerchantUser.merchant_id == merchant.id
            )
        )
        if already_member is not None:
            raise user_exists()
        user = existing
    else:
        user = User(
            email=normalized,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            status=UserStatus.ACTIVE.value,
        )
        session.add(user)
        session.flush()

    if data.role != MerchantRole.OWNER:
        current = session.scalar(
            select(func.count(MerchantUser.id)).where(
                MerchantUser.merchant_id == merchant.id,
                MerchantUser.status == UserStatus.ACTIVE.value,
                MerchantUser.role != MerchantRole.OWNER.value,
            )
        )
        if current is not None and int(current) >= plan.max_staff:
            raise plan_limit_reached("staff", plan.max_staff)
    membership = MerchantUser(
        user_id=user.id,
        merchant_id=merchant.id,
        role=data.role.value,
        status=UserStatus.ACTIVE.value,
    )
    session.add(membership)
    session.flush()
    return membership, SessionUser.model_validate(user)


def update_merchant_user(
    session: Session,
    merchant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MerchantUserUpdate,
) -> tuple[MerchantUser, User]:
    membership = session.scalar(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_id, MerchantUser.user_id == user_id
        )
    )
    if membership is None:
        raise not_found("Usuario del comercio")
    user = session.get(User, membership.user_id)
    if user is None:
        raise not_found("Usuario del comercio")

    # Reactivar al personal también consume hueco del plan (coherente con
    # tiendas §FASE 14): un empleado activo ocupa sitio.
    merchant = session.get(Merchant, merchant_id)
    if (
        data.status == UserStatus.ACTIVE.value
        and membership.status != UserStatus.ACTIVE.value
        and membership.role != MerchantRole.OWNER.value
        and merchant is not None
    ):
        plan = get_plan(merchant.plan)
        current = session.scalar(
            select(func.count(MerchantUser.id)).where(
                MerchantUser.merchant_id == merchant_id,
                MerchantUser.status == UserStatus.ACTIVE.value,
                MerchantUser.role != MerchantRole.OWNER.value,
            )
        )
        if current is not None and int(current) >= plan.max_staff:
            raise plan_limit_reached("staff", plan.max_staff)

    if data.role is not None:
        membership.role = data.role.value
    if data.status is not None:
        membership.status = data.status
    if data.display_name is not None:
        user.display_name = data.display_name
    session.flush()
    return membership, user


def remove_owner_guard(session: Session, merchant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Impide dejar el comercio sin propietario (último `owner` no se degrada)."""
    owners = session.scalars(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_id,
            MerchantUser.role == MerchantRole.OWNER.value,
            MerchantUser.status == UserStatus.ACTIVE.value,
        )
    ).all()
    target = next((o for o in owners if o.user_id == user_id), None)
    if target is not None and len(owners) <= 1:
        raise not_found("Usuario del comercio")
