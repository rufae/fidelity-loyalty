"""API de Wallet (§12.6, §15).

La emisión es un **trabajo** con estado persistido: la petición devuelve
`202` y el panel puede reintentar. Un proveedor sin configurar produce un
trabajo fallido con error claro, nunca una excepción 500 (§6.1).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import DbSession, merchant_access
from app.core.config import Settings, get_settings
from app.domain.errors import not_found
from app.domain.roles import MERCHANT_ADMIN_ROLES, MERCHANT_OPERATOR_ROLES
from app.models.members import Membership
from app.schemas.wallet import JobOut, PassOut
from app.services import wallet as wallet_service
from app.services.audit import record_audit

router = APIRouter(prefix="/merchants/{merchant_id}", tags=["wallet"])

operator = merchant_access(MERCHANT_OPERATOR_ROLES)
admin = merchant_access(MERCHANT_ADMIN_ROLES)


def _membership_in_scope(
    session: DbSession, merchant_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership:
    membership = session.get(Membership, membership_id)
    if membership is None or str(membership.merchant_id) != str(merchant_id):
        raise not_found("Membresía")
    return membership


@router.post("/memberships/{membership_id}/wallet/issue", response_model=PassOut, status_code=202)
def issue(
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(operator)],
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
) -> PassOut:
    membership = _membership_in_scope(session, merchant_id, membership_id)
    job, wallet_pass = wallet_service.issue_pass(session, membership, settings)
    record_audit(
        session,
        action="wallet.issue",
        entity_type="wallet_pass",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(wallet_pass.id),
        metadata={"reason": job.status},
    )
    session.commit()
    if job.status != "succeeded":
        # 202: el trabajo quedó registrado; el error es visible y reintenable.
        response.status_code = 202
    return PassOut(
        id=wallet_pass.id,
        provider=wallet_pass.provider,
        status=wallet_pass.status,
        simulated=bool(wallet_pass.simulated),
        provider_object_id=wallet_pass.provider_object_id,
        last_error_code=wallet_pass.last_error_code,
        last_error_detail=wallet_pass.last_error_detail,
        job_id=job.id,
        job_status=job.status,
    )


@router.get("/wallet/passes", response_model=list[PassOut])
def list_passes(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(admin)],  # noqa: ARG001
) -> list[PassOut]:
    return [
        PassOut(
            id=p.id,
            provider=p.provider,
            status=p.status,
            simulated=bool(p.simulated),
            provider_object_id=p.provider_object_id,
            last_error_code=p.last_error_code,
            last_error_detail=p.last_error_detail,
        )
        for p in wallet_service.list_passes(session, merchant_id)
    ]


@router.get("/wallet/jobs", response_model=list[JobOut])
def list_jobs(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(admin)],  # noqa: ARG001
) -> list[JobOut]:
    return [JobOut.model_validate(job) for job in wallet_service.list_jobs(session, merchant_id)]


@router.post("/wallet/jobs/{job_id}/retry", response_model=JobOut)
def retry_wallet_job(
    merchant_id: uuid.UUID,
    job_id: uuid.UUID,
    session: DbSession,
    context: Annotated[object, Depends(admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JobOut:
    """Reintento manual de un trabajo fallido (§18.2): sin duplicar pases.

    Conserva la clave de idempotencia y las referencias del trabajo: un
    reintento nunca crea recursos repetidos ni toca el ledger.
    """
    job, membership = wallet_service.job_in_scope(session, merchant_id, job_id)
    wallet_service.retry_job(session, job, membership, settings)
    record_audit(
        session,
        action="wallet.job_retried",
        entity_type="background_job",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(job.id),
        metadata={"new_status": job.status, "reason": ""},
    )
    session.commit()
    return JobOut.model_validate(job)
