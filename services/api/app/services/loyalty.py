"""Servicio de programas de fidelización (§7).

Las transiciones de estado son explícitas: nada pasa de `draft` a `archived`
por un JSON malicioso, y publicar exige condiciones visibles (§7.2, §13.4).
"""

import re
import unicodedata
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import DomainError, not_found, slug_conflict
from app.domain.notices import PRIVACY_NOTICE_VERSION
from app.models.loyalty import LoyaltyProgram, ProgramReward, ProgramStatus, ProgramType
from app.models.merchant import Merchant
from app.models.user import utcnow
from app.schemas.loyalty import (
    ProgramCreate,
    ProgramUpdate,
    RewardCreate,
    RewardUpdate,
)
from app.services import locations as locations_service


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:60] or "programa"


def _unique_program_slug(session: Session, merchant_id: uuid.UUID, base: str) -> str:
    slug = _slugify(base)
    candidate = slug
    suffix = 2
    while (
        session.scalar(
            select(LoyaltyProgram.id).where(
                LoyaltyProgram.merchant_id == merchant_id, LoyaltyProgram.slug == candidate
            )
        )
        is not None
    ):
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def get_program(session: Session, merchant_id: uuid.UUID, program_id: uuid.UUID) -> LoyaltyProgram:
    program = session.scalar(
        select(LoyaltyProgram).where(
            LoyaltyProgram.id == program_id, LoyaltyProgram.merchant_id == merchant_id
        )
    )
    if program is None:
        # Idéntico exista o no el programa: sin enumeración entre comercios (§8.2).
        raise not_found("Programa")
    return program


def list_programs(session: Session, merchant_id: uuid.UUID) -> list[LoyaltyProgram]:
    rows = session.scalars(
        select(LoyaltyProgram).where(LoyaltyProgram.merchant_id == merchant_id)
    ).all()
    return sorted(rows, key=lambda p: p.created_at, reverse=True)


def create_program(session: Session, merchant_id: uuid.UUID, data: ProgramCreate) -> LoyaltyProgram:
    program = LoyaltyProgram(
        merchant_id=merchant_id,
        name=data.name.strip(),
        slug=_unique_program_slug(session, merchant_id, data.name),
        program_type=data.program_type,
        description=data.description,
        terms=data.terms,
        stamps_expire_days=data.stamps_expire_days,
        points_per_euro=data.points_per_euro,
        status=ProgramStatus.DRAFT,
    )
    session.add(program)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise slug_conflict() from exc
    return program


def update_program(
    session: Session, program: LoyaltyProgram, data: ProgramUpdate
) -> LoyaltyProgram:
    if data.name is not None:
        program.name = data.name.strip()
    if data.description is not None:
        program.description = data.description
    if data.terms is not None:
        # Las condiciones visibles cambian: se versionan (§7.2).
        if program.terms != data.terms:
            program.terms_version += 1
        program.terms = data.terms
    if "stamps_expire_days" in data.model_fields_set:
        # Presente (número o null): cambia la regla para los `earn`
        # futuros; los lotes ya emitidos conservan su fecha de caducidad.
        program.stamps_expire_days = data.stamps_expire_days
    if "points_per_euro" in data.model_fields_set:
        program.points_per_euro = data.points_per_euro
    session.flush()
    return program


def _require_terms(program: LoyaltyProgram) -> None:
    if not (program.terms and program.terms.strip()):
        raise DomainError(
            422,
            "program_terms_required",
            "El programa necesita condiciones visibles antes de publicarse",
        )
    if program.program_type == ProgramType.POINTS and not program.points_per_euro:
        # Un programa de puntos sin regla no sabe cuánto otorga (§7.6).
        raise DomainError(
            422,
            "points_rule_required",
            "Define los puntos por euro antes de publicar un programa de puntos",
        )


def publish_program(session: Session, program: LoyaltyProgram) -> LoyaltyProgram:
    if program.status not in {ProgramStatus.DRAFT, ProgramStatus.PAUSED}:
        raise DomainError(
            409,
            "invalid_program_transition",
            "Solo un programa borrador o en pausa puede publicarse",
        )
    _require_terms(program)
    # Límite del plan: programas **en vivo** simultáneos (§3.3, tasks.md §5).
    # Se comprueba antes de activar; los borradores no consumen límite.
    locations_service.ensure_program_slot(session, program.merchant_id)
    program.status = ProgramStatus.ACTIVE
    program.published_at = program.published_at or utcnow()
    session.flush()
    return program


def pause_program(session: Session, program: LoyaltyProgram) -> LoyaltyProgram:
    if program.status != ProgramStatus.ACTIVE:
        raise DomainError(
            409, "invalid_program_transition", "Solo un programa activo puede pausarse"
        )
    program.status = ProgramStatus.PAUSED
    session.flush()
    return program


def archive_program(session: Session, program: LoyaltyProgram) -> LoyaltyProgram:
    if program.status == ProgramStatus.ARCHIVED:
        raise DomainError(409, "invalid_program_transition", "El programa ya está archivado")
    program.status = ProgramStatus.ARCHIVED
    session.flush()
    return program


def list_rewards(session: Session, program_id: uuid.UUID) -> list[ProgramReward]:
    rows = session.scalars(
        select(ProgramReward).where(ProgramReward.program_id == program_id)
    ).all()
    return sorted(rows, key=lambda r: (r.stamps_required, r.name))


def create_reward(session: Session, program: LoyaltyProgram, data: RewardCreate) -> ProgramReward:
    reward = ProgramReward(
        program_id=program.id,
        name=data.name,
        description=data.description,
        stamps_required=data.stamps_required,
    )
    session.add(reward)
    session.flush()
    return reward


def update_reward(session: Session, reward: ProgramReward, data: RewardUpdate) -> ProgramReward:
    if data.name is not None:
        reward.name = data.name.strip()
    if data.description is not None:
        reward.description = data.description
    if data.stamps_required is not None:
        reward.stamps_required = data.stamps_required
    if data.status is not None:
        reward.status = data.status
    session.flush()
    return reward


def get_reward(session: Session, program_id: uuid.UUID, reward_id: uuid.UUID) -> ProgramReward:
    reward = session.scalar(
        select(ProgramReward).where(
            ProgramReward.id == reward_id, ProgramReward.program_id == program_id
        )
    )
    if reward is None:
        raise not_found("Recompensa")
    return reward


def public_program_payload(
    session: Session, merchant_slug: str, program_slug: str
) -> dict[str, object]:
    """Datos de la página pública de alta (§12.5, §13.4)."""
    merchant = session.scalar(select(Merchant).where(Merchant.slug == merchant_slug))
    if merchant is None:
        raise not_found("Programa")
    program = session.scalar(
        select(LoyaltyProgram).where(
            LoyaltyProgram.merchant_id == merchant.id,
            LoyaltyProgram.slug == program_slug,
        )
    )
    if program is None:
        raise not_found("Programa")

    rewards = [r for r in list_rewards(session, program.id) if r.is_active]
    published: datetime | None = program.published_at
    return {
        "merchant_name": merchant.name,
        "merchant_slug": merchant.slug,
        "program_name": program.name,
        "program_slug": program.slug,
        "program_type": program.program_type,
        "description": program.description,
        "terms": program.terms,
        "terms_version": program.terms_version,
        "rewards": [
            {"name": r.name, "description": r.description, "stamps_required": r.stamps_required}
            for r in rewards
        ],
        "enrollment_open": program.status == ProgramStatus.ACTIVE and published is not None,
        # Versión del aviso de privacidad del alta (ADR-0006): la conserva
        # el backend para poder acreditar qué versión aceptó el cliente.
        "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        # Caducidad opcional de sellos (§7.7): el alta la comunica antes
        # de registrar al cliente.
        "stamps_expire_days": program.stamps_expire_days,
        # Regla de puntos por euro si procede (§7.6): el alta la explica.
        "points_per_euro": program.points_per_euro,
    }
