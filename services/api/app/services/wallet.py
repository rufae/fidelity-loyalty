"""Servicio de Wallet: emisión y actualización como trabajos (§15, §6.6).

Comportamiento:
- La operación de fidelización **primero** se confirma en el ledger; la
  sincronización con el proveedor es un `background_jobs` aparte. Un fallo
  externo **nunca** revierte ni bloquea sellos/canjes (§6.1).
- El primer intento se ejecuta al crear el trabajo (respuesta rápida) y, si
  falla de forma recuperable, el trabajo pasa a `retrying` con `backoff` y lo
  retoma el worker (`app/workers/runner.py`) hasta `wallet_job_max_attempts`;
  agotados los intentos queda en `failed` (dead-letter) y se puede reintentar
  a mano desde el panel (§15, §18).
- Un proveedor `not_configured` no reintenta (no es un fallo transitorio):
  queda documentado y la tarjeta web sigue funcionando (§6.1, §28).
"""

import hashlib
import hmac
import logging
import uuid
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.errors import DomainError
from app.domain.tokens import get_session_secret
from app.integrations.wallet import get_wallet_provider
from app.integrations.wallet.base import (
    AddToWalletAction,
    PassContext,
    PassResult,
    ProviderStatus,
)
from app.models.loyalty import LoyaltyProgram
from app.models.members import Membership
from app.models.merchant import Merchant
from app.models.user import utcnow
from app.models.wallet import BackgroundJob, JobStatus, WalletPass

#: Errores que no se reintentan: falta configuración, no tiempo de red.
PERMANENT_ERROR_CODES = frozenset({"wallet_provider_not_configured", "wallet_provider_disabled"})

logger = logging.getLogger(__name__)


def pass_context(session: Session, membership: Membership, settings: Settings) -> PassContext:
    """Datos visibles del pase, siempre desde el backend (§6.1, §6.3).

    El barcode lleva la URL absoluta de la tarjeta web: el lector del comercio
    extrae el código opaco y consulta al servidor; nunca hay PII en el QR.
    """
    merchant = session.get(Merchant, membership.merchant_id)
    program = session.get(LoyaltyProgram, membership.program_id)
    base = settings.public_base_url.rstrip("/")
    # Token estable por pase para el servicio web de Apple (§6.4): sin él el
    # pase sería estático y los sellos mostrados nunca cambiarían.
    auth_token = authentication_token(settings, membership.id)
    web_service_url = f"{base}/api/v1" if settings.wallet_provider == "apple" else None
    return PassContext(
        merchant_name=merchant.name if merchant else "Comercio",
        program_name=program.name if program else "Programa",
        stamps=membership.stamps,
        barcode_value=f"{base}/card/{membership.public_token}",
        serial=membership.id.hex,
        authentication_token=auth_token,
        web_service_url=web_service_url,
        base_url=base,
    )


def authentication_token(settings: Settings, membership_id: uuid.UUID) -> str:
    """Token PassKit **determinista** por membresía (§6.4).

    HMAC sobre el id de la membresía con el secreto del servidor: estable sin
    depender del orden de emisión, no adivinable y revocable rotando el
    secreto. Nunca se expone a los usuarios ni al frontend.
    """
    return hmac.new(
        get_session_secret(settings).encode(),
        f"passkit-auth:{membership_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def add_to_wallet_actions(
    session: Session, membership: Membership, settings: Settings
) -> tuple[list[AddToWalletAction], bool]:
    """Acciones «Añadir a Wallet» reales del proveedor configurado (§6.7).

    Devuelve (acciones, simulated). Con proveedor simulado la interfaz debe
    rotularlo como modo demostración y ofrecer la tarjeta web (§17.2).
    """
    provider = get_wallet_provider(settings)
    context = pass_context(session, membership, settings)
    action = provider.get_add_to_wallet_action(membership.public_token, context)
    return [action], action.simulated


def _pass_for(session: Session, membership_id: uuid.UUID, provider: str) -> WalletPass | None:
    return session.scalar(
        select(WalletPass).where(
            WalletPass.membership_id == membership_id, WalletPass.provider == provider
        )
    )


def _record_result(
    session: Session, membership: Membership, provider: str, result: PassResult
) -> WalletPass:
    wallet_pass = _pass_for(session, membership.id, provider) or WalletPass(
        merchant_id=membership.merchant_id,
        membership_id=membership.id,
        provider=provider,
    )
    wallet_pass.provider = provider
    wallet_pass.simulated = 1 if result.simulated else 0
    wallet_pass.last_updated_at = utcnow()
    if result.status in {ProviderStatus.TEST, ProviderStatus.ACTIVE}:
        wallet_pass.status = "issued"
        wallet_pass.provider_object_id = result.provider_object_id
        wallet_pass.last_issued_at = utcnow()
        wallet_pass.last_error_code = None
        wallet_pass.last_error_detail = None
    else:
        wallet_pass.status = (
            "error" if result.status == ProviderStatus.ERROR else result.status.value
        )
        wallet_pass.last_error_code = result.status.value
        wallet_pass.last_error_detail = (result.detail or "")[:255] or None
    session.add(wallet_pass)
    session.flush()
    return wallet_pass


def _backoff(attempts: int, settings: Settings) -> timedelta:
    """Backoff lineal acotado: 1×, 2×, 3×… el intervalo base (máx. 1 hora)."""
    seconds = min(settings.wallet_job_backoff_seconds * attempts, 3600)
    return timedelta(seconds=seconds)


def _run_job(
    session: Session,
    job: BackgroundJob,
    membership: Membership,
    settings: Settings,
    operation: str,
) -> WalletPass:
    provider = get_wallet_provider(settings)
    job.status = JobStatus.RUNNING
    job.started_at = utcnow()
    job.attempts += 1
    job.next_attempt_at = None
    session.flush()

    context = pass_context(session, membership, settings)
    try:
        if operation == "issue":
            result = provider.issue_pass(membership.id, membership.public_token, context)
        else:
            result = provider.update_pass(membership.id, membership.public_token, context)
    except Exception as error:  # noqa: BLE001 — regla irrenunciable §6.1
        # Cualquier excepción del proveedor (certificado corrupto, clave
        # cifrada, error de red no capturado) se convierte en un resultado de
        # error del trabajo. Jamás puede propagarse: eso revertiría la
        # operación del ledger ya confirmada en la misma transacción.
        logger.warning(
            "wallet %s falló con excepción: %s",
            operation,
            type(error).__name__,
        )
        result = PassResult(
            provider_object_id="",
            status=ProviderStatus.ERROR,
            simulated=False,
            detail=f"Error del proveedor ({type(error).__name__})",
        )

    wallet_pass = _record_result(session, membership, provider.name, result)
    if result.status in {ProviderStatus.TEST, ProviderStatus.ACTIVE}:
        job.status = JobStatus.SUCCEEDED
        job.completed_at = utcnow()
        job.error_code = None
        job.error_detail = None
    else:
        error_code = (
            "wallet_provider_not_configured"
            if result.status == ProviderStatus.NOT_CONFIGURED
            else ("wallet_issue_failed" if operation == "issue" else "wallet_update_failed")
        )
        job.error_code = error_code
        job.error_detail = (result.detail or "")[:255] or None
        permanent = error_code in PERMANENT_ERROR_CODES
        if not permanent and job.attempts < settings.wallet_job_max_attempts:
            # Recuperable: queda a la espera del worker (§15).
            job.status = JobStatus.RETRYING
            job.next_attempt_at = utcnow() + _backoff(job.attempts, settings)
            job.completed_at = None
        else:
            # Dead-letter: sin más intentos automáticos; reintento manual.
            job.status = JobStatus.FAILED
            job.completed_at = utcnow()
    session.flush()
    return wallet_pass


def issue_pass(
    session: Session,
    membership: Membership,
    settings: Settings,
    *,
    idempotency_key: str | None = None,
) -> tuple[BackgroundJob, WalletPass]:
    """Emite (o intenta emitir) el pase de la membresía en el proveedor activo."""
    existing_job = None
    if idempotency_key:
        existing_job = session.scalar(
            select(BackgroundJob).where(
                BackgroundJob.idempotency_key == idempotency_key,
                BackgroundJob.entity_type == "membership",
                BackgroundJob.entity_id == str(membership.id),
            )
        )
    if existing_job is not None:
        # Idempotencia real (§15): una misma clave nunca lanza otra emisión,
        # aunque el trabajo haya fallado o esté en reintento (el fallo se ve
        # en el estado del trabajo y se reacciona con el reintento manual).
        existing_pass = _pass_for(session, membership.id, settings.wallet_provider)
        if existing_pass is not None:
            return existing_job, existing_pass
        raise DomainError(409, "duplicate_operation", "Operación ya registrada")

    job = BackgroundJob(
        job_type="wallet.issue",
        entity_type="membership",
        entity_id=str(membership.id),
        idempotency_key=idempotency_key,
    )
    session.add(job)
    session.flush()
    wallet_pass = _run_job(session, job, membership, settings, "issue")
    return job, wallet_pass


def update_passes_after_operation(
    session: Session, membership: Membership, settings: Settings
) -> list[BackgroundJob]:
    """Tras un movimiento de sellos, intenta sincronizar los pases existentes.

    Un fallo **nunca revierte** el movimiento del ledger (§6.1, §15): solo deja
    el trabajo en `retrying`/`failed` visible para reintentar.
    """
    passes = session.scalars(
        select(WalletPass).where(
            WalletPass.membership_id == membership.id,
            WalletPass.status == "issued",
        )
    ).all()
    jobs: list[BackgroundJob] = []
    for _existing_pass in passes:
        job = BackgroundJob(
            job_type="wallet.update",
            entity_type="membership",
            entity_id=str(membership.id),
            # Clave determinista por versión de la membresía (§15): dos
            # operaciones no comparten trabajo, una repetición no duplica.
            idempotency_key=f"wallet.update:{membership.id}:{membership.version}",
        )
        session.add(job)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            continue
        _run_job(session, job, membership, settings, "update")
        jobs.append(job)
    return jobs


def due_jobs(session: Session, now_limit: int = 50) -> list[tuple[BackgroundJob, Membership]]:
    """Trabajos vencidos de reintento (worker, §15)."""
    now = utcnow()
    rows = session.scalars(
        select(BackgroundJob)
        .where(
            BackgroundJob.status.in_([JobStatus.QUEUED, JobStatus.RETRYING]),
            or_(
                BackgroundJob.next_attempt_at.is_(None),
                BackgroundJob.next_attempt_at <= now,
            ),
        )
        .order_by(BackgroundJob.created_at)
        .limit(now_limit)
    ).all()
    pending: list[tuple[BackgroundJob, Membership]] = []
    for job in rows:
        if job.entity_type != "membership":
            continue
        membership = session.get(Membership, uuid.UUID(job.entity_id))
        if membership is not None:
            pending.append((job, membership))
    return pending


def run_due_jobs(session: Session, settings: Settings) -> int:
    """Ejecuta los trabajos vencidos. Devuelve cuántos ha procesado."""
    processed = 0
    for job, membership in due_jobs(session):
        _run_job(
            session,
            job,
            membership,
            settings,
            "issue" if job.job_type == "wallet.issue" else "update",
        )
        processed += 1
    return processed


def retry_job(
    session: Session, job: BackgroundJob, membership: Membership, settings: Settings
) -> BackgroundJob:
    """Reintento manual de un trabajo agotado (§18.2), sin duplicar recursos.

    Conserva su `idempotency_key` y sus referencias: un reintento no crea pases
    duplicados ni movimientos nuevos.
    """
    if job.status not in {JobStatus.FAILED, JobStatus.RETRYING, JobStatus.CANCELLED}:
        return job
    job.status = JobStatus.QUEUED
    job.next_attempt_at = None
    # El reintento manual no se queda sin intentos: se reserva un intento más.
    # Contador separado para reintentos manuales: `attempts` conserva el
    # histórico real (antes el contador quedaba plano y se perdía la señal).
    job.manual_retries += 1
    session.flush()
    _run_job(
        session,
        job,
        membership,
        settings,
        "issue" if job.job_type == "wallet.issue" else "update",
    )
    return job


def list_passes(session: Session, merchant_id: uuid.UUID) -> list[WalletPass]:
    rows = session.scalars(select(WalletPass).where(WalletPass.merchant_id == merchant_id)).all()
    return sorted(rows, key=lambda p: p.created_at, reverse=True)


def list_jobs(session: Session, merchant_id: uuid.UUID) -> list[BackgroundJob]:
    """Trabajos del comercio: los de membresías de este comercio."""
    membership_ids = [
        m.id
        for m in session.scalars(
            select(Membership).where(Membership.merchant_id == merchant_id)
        ).all()
    ]
    if not membership_ids:
        return []
    rows = session.scalars(
        select(BackgroundJob)
        .where(
            BackgroundJob.entity_type == "membership",
            BackgroundJob.entity_id.in_([str(m) for m in membership_ids]),
        )
        .order_by(BackgroundJob.created_at.desc())
    ).all()
    return list(rows)


def job_in_scope(
    session: Session, merchant_id: uuid.UUID, job_id: uuid.UUID
) -> tuple[BackgroundJob, Membership]:
    """Trabajo y membresía del comercio; lo ajeno responde como inexistente (§8.2)."""
    job = session.get(BackgroundJob, job_id)
    if job is None or job.entity_type != "membership":
        raise DomainError(404, "job_not_found", "Trabajo no encontrado")
    membership = session.get(Membership, uuid.UUID(job.entity_id))
    if membership is None or membership.merchant_id != merchant_id:
        raise DomainError(404, "job_not_found", "Trabajo no encontrado")
    return job, membership
