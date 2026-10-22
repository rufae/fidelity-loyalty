"""API de programas y recompensas del comercio (§12.4).

Todos los endpoints exigen rol de administración del comercio (`owner`/`admin`)
vía `merchant_access`, nunca confiando en parámetros del cliente (§8.2).
"""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, merchant_access
from app.domain.roles import MERCHANT_ADMIN_ROLES
from app.models.loyalty import LoyaltyProgram
from app.schemas.loyalty import (
    ProgramCreate,
    ProgramDetailOut,
    ProgramOut,
    ProgramUpdate,
    RewardCreate,
    RewardOut,
    RewardUpdate,
)
from app.services import loyalty as loyalty_service
from app.services.audit import record_audit

router = APIRouter(prefix="/merchants/{merchant_id}/programs", tags=["programas"])

merchant_admin = merchant_access(MERCHANT_ADMIN_ROLES)


def _detail(session: DbSession, program: LoyaltyProgram) -> ProgramDetailOut:
    rewards = loyalty_service.list_rewards(session, program.id)
    return ProgramDetailOut(
        **ProgramOut.model_validate(program).model_dump(),
        rewards=[RewardOut.model_validate(r) for r in rewards],
    )


@router.get("", response_model=list[ProgramOut])
def list_programs(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],  # noqa: ARG001
) -> list[ProgramOut]:
    return [
        ProgramOut.model_validate(p) for p in loyalty_service.list_programs(session, merchant_id)
    ]


@router.post("", response_model=ProgramDetailOut, status_code=201)
def create_program(
    merchant_id: uuid.UUID,
    data: ProgramCreate,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],
) -> ProgramDetailOut:
    program = loyalty_service.create_program(session, merchant_id, data)
    record_audit(
        session,
        action="program.created",
        entity_type="loyalty_program",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(program.id),
    )
    session.commit()
    return _detail(session, program)


@router.get("/{program_id}", response_model=ProgramDetailOut)
def get_program(
    merchant_id: uuid.UUID,
    program_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],  # noqa: ARG001
) -> ProgramDetailOut:
    program = loyalty_service.get_program(session, merchant_id, program_id)
    return _detail(session, program)


@router.patch("/{program_id}", response_model=ProgramDetailOut)
def update_program(
    merchant_id: uuid.UUID,
    program_id: uuid.UUID,
    data: ProgramUpdate,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],
) -> ProgramDetailOut:
    program = loyalty_service.get_program(session, merchant_id, program_id)
    program = loyalty_service.update_program(session, program, data)
    record_audit(
        session,
        action="program.updated",
        entity_type="loyalty_program",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(program.id),
        metadata={"fields": sorted(data.model_fields_set)},
    )
    session.commit()
    return _detail(session, program)


def _transition(name: str) -> Callable[..., ProgramDetailOut]:
    def endpoint(
        merchant_id: uuid.UUID,
        program_id: uuid.UUID,
        session: DbSession,
        context: Annotated[object, Depends(merchant_admin)],
    ) -> ProgramDetailOut:
        program = loyalty_service.get_program(session, merchant_id, program_id)
        program = {
            "publish": loyalty_service.publish_program,
            "pause": loyalty_service.pause_program,
            "archive": loyalty_service.archive_program,
        }[name](session, program)
        record_audit(
            session,
            action=f"program.{name}ed" if name != "publish" else "program.published",
            entity_type="loyalty_program",
            actor_id=context.user.id,  # type: ignore[attr-defined]
            merchant_id=merchant_id,
            entity_id=str(program.id),
            metadata={"new_status": program.status},
        )
        session.commit()
        return _detail(session, program)

    return endpoint


router.post("/{program_id}/publish", response_model=ProgramDetailOut)(_transition("publish"))
router.post("/{program_id}/pause", response_model=ProgramDetailOut)(_transition("pause"))
router.post("/{program_id}/archive", response_model=ProgramDetailOut)(_transition("archive"))


@router.get("/{program_id}/rewards", response_model=list[RewardOut])
def list_rewards(
    merchant_id: uuid.UUID,
    program_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],  # noqa: ARG001
) -> list[RewardOut]:
    loyalty_service.get_program(session, merchant_id, program_id)
    return [RewardOut.model_validate(r) for r in loyalty_service.list_rewards(session, program_id)]


@router.post("/{program_id}/rewards", response_model=RewardOut, status_code=201)
def create_reward(
    merchant_id: uuid.UUID,
    program_id: uuid.UUID,
    data: RewardCreate,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],
) -> RewardOut:
    program = loyalty_service.get_program(session, merchant_id, program_id)
    reward = loyalty_service.create_reward(session, program, data)
    record_audit(
        session,
        action="reward.created",
        entity_type="program_reward",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(reward.id),
    )
    session.commit()
    return RewardOut.model_validate(reward)


@router.patch("/{program_id}/rewards/{reward_id}", response_model=RewardOut)
def update_reward(
    merchant_id: uuid.UUID,
    program_id: uuid.UUID,
    reward_id: uuid.UUID,
    data: RewardUpdate,
    session: DbSession,
    context: Annotated[object, Depends(merchant_admin)],
) -> RewardOut:
    loyalty_service.get_program(session, merchant_id, program_id)
    reward = loyalty_service.get_reward(session, program_id, reward_id)
    reward = loyalty_service.update_reward(session, reward, data)
    record_audit(
        session,
        action="reward.updated",
        entity_type="program_reward",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(reward.id),
        metadata={"fields": sorted(data.model_fields_set)},
    )
    session.commit()
    return RewardOut.model_validate(reward)
