"""Analítica del comercio (§12.9, §24.2).

Todas las cifras se calculan **desde la base de datos**, nunca se inventan
(§13.2). Los clics de reseñas se llaman `review_link_clicks`: jamás
«reseñas recibidas» (§4.4).
"""

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ledger import LoyaltyTransaction, RewardRedemption, TransactionType
from app.models.loyalty import LoyaltyProgram, ProgramReward, ProgramStatus
from app.models.members import Member, Membership
from app.models.merchant import Merchant, MerchantLocation
from app.models.nfc import NfcTag, RedirectEvent, TagStatus, TagType
from app.models.wallet import WalletPass

#: Zona horaria por omisión si el comercio guardara un valor inválido (no
#: debería ocurrir: se valida al crear, pero fail-soft en analítica).
_FALLBACK_TZ = "Europe/Madrid"


def _merchant_day_start_utc(session: Session, merchant_id: uuid.UUID) -> tuple[datetime, str]:
    """Inicio del día «hoy» del comercio en UTC, y su fecha local (ISO).

    El ledger guarda UTC (§11.19): «hoy» es hoy en la **zona horaria del
    comercio**, convertido a UTC para filtrar (§24.2).
    """
    merchant = session.get(Merchant, merchant_id)
    try:
        tz = ZoneInfo(merchant.timezone if merchant else _FALLBACK_TZ)
    except Exception:  # noqa: BLE001 — valor inválido: fail-soft con la base.
        tz = ZoneInfo(_FALLBACK_TZ)
    local_now = datetime.now(tz)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(UTC), local_now.date().isoformat()


def today_summary(session: Session, merchant_id: uuid.UUID) -> dict[str, object]:
    """Cierre de turno (§13.2): qué ha pasado hoy en el comercio.

    Son valores **del día** (no acumulados), calculados desde la base de
    datos en la zona horaria del comercio.
    """
    day_start_utc, local_date = _merchant_day_start_utc(session, merchant_id)
    enrolled = (
        session.scalar(
            select(func.count(Membership.id)).where(
                Membership.merchant_id == merchant_id, Membership.joined_at >= day_start_utc
            )
        )
        or 0
    )
    stamps = (
        session.scalar(
            select(func.coalesce(func.sum(LoyaltyTransaction.quantity), 0)).where(
                LoyaltyTransaction.merchant_id == merchant_id,
                LoyaltyTransaction.transaction_type == TransactionType.EARN,
                LoyaltyTransaction.created_at >= day_start_utc,
            )
        )
        or 0
    )
    redeemed_stamps = (
        session.scalar(
            select(func.coalesce(func.sum(-LoyaltyTransaction.quantity), 0)).where(
                LoyaltyTransaction.merchant_id == merchant_id,
                LoyaltyTransaction.transaction_type == TransactionType.REDEEM,
                LoyaltyTransaction.created_at >= day_start_utc,
            )
        )
        or 0
    )
    redemptions = (
        session.scalar(
            select(func.count(RewardRedemption.id)).where(
                RewardRedemption.merchant_id == merchant_id,
                RewardRedemption.redeemed_at >= day_start_utc,
            )
        )
        or 0
    )
    return {
        "local_date": local_date,
        "enrolled_today": int(enrolled),
        "stamps_today": int(stamps),
        "redeemed_stamps_today": int(redeemed_stamps),
        "redemptions_today": int(redemptions),
    }


def summary(session: Session, merchant_id: uuid.UUID) -> dict[str, int]:
    members_total = (
        session.scalar(select(func.count(Member.id)).where(Member.merchant_id == merchant_id)) or 0
    )
    memberships_active = (
        session.scalar(
            select(func.count(Membership.id)).where(
                Membership.merchant_id == merchant_id, Membership.status == "active"
            )
        )
        or 0
    )
    stamps_granted = (
        session.scalar(
            select(func.coalesce(func.sum(LoyaltyTransaction.quantity), 0)).where(
                LoyaltyTransaction.merchant_id == merchant_id,
                LoyaltyTransaction.transaction_type == TransactionType.EARN,
            )
        )
        or 0
    )
    stamps_redeemed = (
        session.scalar(
            select(func.coalesce(func.sum(-LoyaltyTransaction.quantity), 0)).where(
                LoyaltyTransaction.merchant_id == merchant_id,
                LoyaltyTransaction.transaction_type == TransactionType.REDEEM,
            )
        )
        or 0
    )
    redemptions = (
        session.scalar(
            select(func.count(RewardRedemption.id)).where(
                RewardRedemption.merchant_id == merchant_id
            )
        )
        or 0
    )
    wallet_passes = (
        session.scalar(
            select(func.count(WalletPass.id)).where(WalletPass.merchant_id == merchant_id)
        )
        or 0
    )
    wallet_errors = (
        session.scalar(
            select(func.count(WalletPass.id)).where(
                WalletPass.merchant_id == merchant_id, WalletPass.status == "error"
            )
        )
        or 0
    )
    clicks = (
        session.scalar(
            select(func.count(RedirectEvent.id)).where(RedirectEvent.merchant_id == merchant_id)
        )
        or 0
    )

    return {
        "members_total": members_total,
        "memberships_active": memberships_active,
        "stamps_granted": int(stamps_granted),
        "stamps_redeemed": int(stamps_redeemed),
        "redemptions": redemptions,
        "wallet_passes": wallet_passes,
        "wallet_errors": wallet_errors,
        # Nombre exacto §4.4: es un clic al enlace, no una reseña.
        "review_link_clicks": clicks,
    }


def onboarding_checklist(session: Session, merchant_id: uuid.UUID) -> dict[str, bool]:
    """Primeros pasos del comercio nuevo (§13.2, mejora de onboarding).

    Cuatro puertas para llegar al primer sello, derivadas de la base de
    datos (nada se inventa en cliente). El Resumen las muestra hasta que
    estén completas y después no vuelve a estorbar. Los enlaces de cada
    paso llevan a la pantalla que lo resuelve; aquí solo se decide qué
    falta. Sin PII: únicamente booleanos de progreso del comercio.
    """
    program_ready = (
        session.scalar(
            select(LoyaltyProgram.id)
            .join(ProgramReward, ProgramReward.program_id == LoyaltyProgram.id)
            .where(
                LoyaltyProgram.merchant_id == merchant_id,
                LoyaltyProgram.status == ProgramStatus.ACTIVE,
                ProgramReward.status == "active",
            )
            .limit(1)
        )
        is not None
    )
    store_ready = (
        session.scalar(
            select(func.count(MerchantLocation.id)).where(
                MerchantLocation.merchant_id == merchant_id,
                MerchantLocation.status == "active",
            )
        )
        or 0
    ) > 0
    qr_ready = (
        session.scalar(
            select(func.count(NfcTag.id)).where(
                NfcTag.merchant_id == merchant_id,
                NfcTag.tag_type == TagType.LOYALTY_SIGNUP,
                NfcTag.status == TagStatus.ACTIVE,
            )
        )
        or 0
    ) > 0
    first_member = (
        session.scalar(select(func.count(Member.id)).where(Member.merchant_id == merchant_id)) or 0
    ) > 0

    return {
        "program_ready": program_ready,
        "store_ready": store_ready,
        "qr_ready": qr_ready,
        "first_member": first_member,
        "completed": program_ready and store_ready and qr_ready and first_member,
    }


def transactions_series(
    session: Session, merchant_id: uuid.UUID, since: datetime | None
) -> list[dict[str, object]]:
    """Serie diaria de operaciones (acumuladas y canjeadas) para la gráfica."""
    query = (
        select(
            func.date(LoyaltyTransaction.created_at).label("day"),
            LoyaltyTransaction.transaction_type,
            func.count(LoyaltyTransaction.id),
        )
        .where(LoyaltyTransaction.merchant_id == merchant_id)
        .group_by("day", LoyaltyTransaction.transaction_type)
        .order_by("day")
    )
    if since is not None:
        query = query.where(LoyaltyTransaction.created_at >= since)
    rows = session.execute(query).all()
    return [
        {"day": str(day), "transaction_type": ttype, "count": count} for day, ttype, count in rows
    ]


def recent_enrollments(
    session: Session, merchant_id: uuid.UUID, since_utc: datetime, limit: int = 12
) -> list[Membership]:
    """Altas del comercio desde `since_utc`, más recientes primero.

    Es la señal del «puente mostrador» (mejora de compra #2): el personal ve
    quién se ha registrado hoy y puede darle la bienvenida con su primer
    sello. Sondeo desde la consola, **no** notificaciones push: una tienda
    con mucho tráfico no debe vivir de avisos.
    """
    rows = session.scalars(
        select(Membership)
        .where(
            Membership.merchant_id == merchant_id,
            Membership.joined_at >= since_utc,
        )
        .order_by(Membership.joined_at.desc())
        .limit(limit)
    ).all()
    return list(rows)
