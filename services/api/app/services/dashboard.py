"""Analítica del comercio (§12.9, §24.2).

Todas las cifras se calculan **desde la base de datos**, nunca se inventan
(§13.2). Los clics de reseñas se llaman `review_link_clicks`: jamás
«reseñas recibidas» (§4.4).
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ledger import LoyaltyTransaction, RewardRedemption, TransactionType
from app.models.members import Member, Membership
from app.models.nfc import RedirectEvent
from app.models.wallet import WalletPass


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
