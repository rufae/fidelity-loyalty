"""Tokens de un solo uso y sesiones acotadas para acceso a tarjetas."""

import hashlib
import secrets
from datetime import timedelta
from typing import Any, TypedDict, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.errors import DomainError
from app.models.card_access import MemberCardSession, MemberEmailToken
from app.models.loyalty import LoyaltyProgram
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.user import utcnow

EMAIL_TOKEN_TTL = timedelta(minutes=30)
CARD_SESSION_TTL = timedelta(days=30)


class MemberCardSummary(TypedDict):
    token: str
    merchant_name: str
    merchant_slug: str
    program_id: str
    program_name: str
    stamps: int


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_email_token(
    session: Session,
    member: Member,
    merchant_id: UUID,
    purpose: str,
    membership_id: UUID | None = None,
) -> str:
    raw = secrets.token_urlsafe(32)
    session.execute(
        update(MemberEmailToken)
        .where(
            MemberEmailToken.member_id == member.id,
            MemberEmailToken.merchant_id == merchant_id,
            MemberEmailToken.purpose == purpose,
            MemberEmailToken.used_at.is_(None),
        )
        .values(used_at=utcnow())
    )
    session.add(
        MemberEmailToken(
            member_id=member.id,
            merchant_id=merchant_id,
            membership_id=membership_id,
            token_hash=_hash(raw),
            purpose=purpose,
            expires_at=utcnow() + EMAIL_TOKEN_TTL,
        )
    )
    session.flush()
    return raw


def consume_email_token(session: Session, raw: str, purpose: str) -> MemberEmailToken:
    """Reclama el token en una sola sentencia condicional (anti-carrera).

    Dos peticiones simultáneas con el mismo enlace no pueden «leer» ambas el
    token como no usado: el `UPDATE ... WHERE used_at IS NULL` es atómico y
    solo una gana (`rowcount == 1`). La otra recibe el error genérico, sin
    distinguir si caducó o ya se usó (§16.4, doble canje).
    """
    now = utcnow()
    claimed = cast(
        "CursorResult[Any]",
        session.execute(
            update(MemberEmailToken)
            .where(
                MemberEmailToken.token_hash == _hash(raw),
                MemberEmailToken.purpose == purpose,
                MemberEmailToken.used_at.is_(None),
                MemberEmailToken.expires_at > now,
            )
            .values(used_at=now)
        ),
    )
    if claimed.rowcount != 1:
        raise DomainError(400, "invalid_or_expired_link", "El enlace no es válido o ha caducado.")
    token = session.scalar(
        select(MemberEmailToken).where(MemberEmailToken.token_hash == _hash(raw))
    )
    if token is None:  # pragma: no cover — reclamado en esta misma transacción
        raise DomainError(400, "invalid_or_expired_link", "El enlace no es válido o ha caducado.")
    return token


def create_card_session(session: Session, member_id: UUID, merchant_id: UUID) -> str:
    raw = secrets.token_urlsafe(32)
    session.add(
        MemberCardSession(
            member_id=member_id,
            merchant_id=merchant_id,
            token_hash=_hash(raw),
            expires_at=utcnow() + CARD_SESSION_TTL,
        )
    )
    session.flush()
    return raw


def card_session_member(session: Session, raw: str, merchant_slug: str) -> tuple[Member, Merchant]:
    merchant = session.scalar(select(Merchant).where(Merchant.slug == merchant_slug))
    if merchant is None:
        raise DomainError(404, "merchant_not_found", "Comercio no encontrado.")
    card_session = session.scalar(
        select(MemberCardSession).where(
            MemberCardSession.token_hash == _hash(raw),
            MemberCardSession.merchant_id == merchant.id,
            MemberCardSession.revoked_at.is_(None),
            MemberCardSession.expires_at > utcnow(),
        )
    )
    if card_session is None:
        raise DomainError(401, "card_session_required", "Solicita un enlace de acceso por correo.")
    member = session.scalar(
        select(Member).where(
            Member.id == card_session.member_id,
            Member.merchant_id == merchant.id,
            Member.email_verified_at.is_not(None),
            Member.status == "active",
        )
    )
    if member is None:
        raise DomainError(401, "card_session_required", "Solicita un enlace de acceso por correo.")
    return member, merchant


def cards_for_member(session: Session, member_id: UUID) -> list[MemberCardSummary]:
    rows = session.execute(
        select(Membership, Merchant.name, Merchant.slug, LoyaltyProgram.name)
        .join(Merchant, Merchant.id == Membership.merchant_id)
        .join(LoyaltyProgram, LoyaltyProgram.id == Membership.program_id)
        .where(
            Membership.member_id == member_id,
            Membership.status == "active",
        )
        .order_by(Membership.joined_at.desc())
    ).all()
    return [
        MemberCardSummary(
            token=membership.public_token,
            merchant_name=merchant_name,
            merchant_slug=merchant_slug,
            program_id=str(membership.program_id),
            program_name=program_name,
            stamps=membership.stamps,
        )
        for membership, merchant_name, merchant_slug, program_name in rows
    ]


def revoke_card_session(session: Session, raw: str, merchant_slug: str) -> None:
    merchant = session.scalar(select(Merchant).where(Merchant.slug == merchant_slug))
    if merchant is None:
        return
    card_session = session.scalar(
        select(MemberCardSession).where(
            MemberCardSession.token_hash == _hash(raw),
            MemberCardSession.merchant_id == merchant.id,
            MemberCardSession.revoked_at.is_(None),
        )
    )
    if card_session is not None:
        card_session.revoked_at = utcnow()
        session.flush()
