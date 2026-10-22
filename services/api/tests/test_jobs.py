"""Trabajos Wallet: reintentos con backoff, dead-letter y reintento manual (§15).

La garantía que protege todo: **un fallo del proveedor Wallet nunca toca el
ledger** (§6.1). Aquí se prueba con un proveedor que falla de verdad.
"""

import uuid
from datetime import timedelta

import pytest
from app.core.config import Settings
from app.integrations.wallet.base import (
    AddToWalletAction,
    PassResult,
    ProviderStatus,
    WalletProvider,
)
from app.models.ledger import LoyaltyTransaction
from app.models.loyalty import LoyaltyProgram
from app.models.members import Member, Membership
from app.models.user import utcnow
from app.models.wallet import JobStatus, WalletPass
from app.services import ledger as ledger_service
from app.services import members as members_service
from app.services import wallet as wallet_service
from sqlalchemy import select
from sqlalchemy.orm import Session

SETTINGS = Settings(
    # El proveedor real se sustituye por un fake fallido en cada prueba; aquí
    # solo interesa la configuración de reintentos.
    wallet_provider="simulated",
    wallet_job_max_attempts=3,
    wallet_job_backoff_seconds=30,
)


class FailingProvider:
    """Proveedor que devuelve ERROR transitorio (red/caída)."""

    name = "apple"

    def status(self) -> ProviderStatus:
        return ProviderStatus.ERROR

    def issue_pass(
        self, membership_id: uuid.UUID, public_token: str, context: object = None
    ) -> PassResult:
        return PassResult("", ProviderStatus.ERROR, False, "proveedor caído")

    def update_pass(
        self, membership_id: uuid.UUID, public_token: str, context: object = None
    ) -> PassResult:
        return PassResult("", ProviderStatus.ERROR, False, "proveedor caído")

    def revoke_pass(
        self, membership_id: uuid.UUID, public_token: str, context: object = None
    ) -> PassResult:
        return PassResult("", ProviderStatus.ERROR, False, "proveedor caído")

    def get_add_to_wallet_action(
        self, public_token: str, context: object = None
    ) -> AddToWalletAction:
        return AddToWalletAction(
            kind="apple", label="Añadir a Apple Wallet", url=None, simulated=False
        )


class NotConfiguredProvider(FailingProvider):
    name = "apple"

    def issue_pass(
        self, membership_id: uuid.UUID, public_token: str, context: object = None
    ) -> PassResult:
        return PassResult("", ProviderStatus.NOT_CONFIGURED, False, "sin credenciales")

    def update_pass(
        self, membership_id: uuid.UUID, public_token: str, context: object = None
    ) -> PassResult:
        return PassResult("", ProviderStatus.NOT_CONFIGURED, False, "sin credenciales")


def _membership(db_session: Session) -> Membership:
    member = Member(merchant_id=uuid.uuid4(), email="cliente@example.com", display_name="Cliente")
    db_session.add(member)
    db_session.flush()
    program = LoyaltyProgram(
        merchant_id=member.merchant_id,
        name="Club",
        slug="club",
        status="active",
        terms="1 sello por visita",
    )
    db_session.add(program)
    db_session.flush()
    membership = Membership(
        merchant_id=member.merchant_id,
        program_id=program.id,
        member_id=member.id,
        public_token=members_service.new_public_token(),
    )
    db_session.add(membership)
    db_session.flush()
    return membership


def _patch_provider(monkeypatch: pytest.MonkeyPatch, provider: WalletProvider) -> None:
    monkeypatch.setattr(wallet_service, "get_wallet_provider", lambda settings: provider)


def test_fallo_recuperable_queda_en_reintento_con_backoff(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _patch_provider(monkeypatch, FailingProvider())
    membership = _membership(db_session)

    job, _pass = wallet_service.issue_pass(db_session, membership, SETTINGS)

    assert job.status == JobStatus.RETRYING
    assert job.attempts == 1
    assert job.next_attempt_at is not None and job.next_attempt_at > utcnow()
    assert job.error_code == "wallet_issue_failed"
    # Backoff acotado: como mucho una hora (§15).
    assert job.next_attempt_at <= utcnow() + timedelta(hours=1)


def test_al_agotar_intentos_pasa_a_dead_letter(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _patch_provider(monkeypatch, FailingProvider())
    membership = _membership(db_session)
    job, _pass = wallet_service.issue_pass(db_session, membership, SETTINGS)

    for _ in range(SETTINGS.wallet_job_max_attempts - 1):
        wallet_service._run_job(db_session, job, membership, SETTINGS, "issue")

    assert job.status == JobStatus.FAILED
    assert job.attempts == SETTINGS.wallet_job_max_attempts
    assert job.next_attempt_at is None


def test_proveedor_no_configurado_no_reintenta(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _patch_provider(monkeypatch, NotConfiguredProvider())
    membership = _membership(db_session)

    job, _pass = wallet_service.issue_pass(db_session, membership, SETTINGS)

    assert job.status == JobStatus.FAILED
    assert job.attempts == 1  # sin reintentos: no es un fallo transitorio
    assert job.error_code == "wallet_provider_not_configured"


def test_el_worker_solo_procesa_los_vencidos(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _patch_provider(monkeypatch, FailingProvider())
    membership = _membership(db_session)
    job, _pass = wallet_service.issue_pass(db_session, membership, SETTINGS)
    assert job.status == JobStatus.RETRYING

    # Con el backoff en el futuro no debe tocarlo todavía.
    assert wallet_service.run_due_jobs(db_session, SETTINGS) == 0
    assert job.attempts == 1

    # Al vencer el plazo, el worker lo retoma.
    job.next_attempt_at = utcnow() - timedelta(seconds=1)
    db_session.flush()
    assert wallet_service.run_due_jobs(db_session, SETTINGS) == 1
    assert job.attempts == 2


def test_reintento_manual_no_duplica_pases(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _patch_provider(monkeypatch, FailingProvider())
    membership = _membership(db_session)
    job, _pass = wallet_service.issue_pass(db_session, membership, SETTINGS)
    for _ in range(SETTINGS.wallet_job_max_attempts - 1):
        wallet_service._run_job(db_session, job, membership, SETTINGS, "issue")
    assert job.status == JobStatus.FAILED

    wallet_service.retry_job(db_session, job, membership, SETTINGS)

    # Mismo trabajo, misma referencia y un único registro de pase por proveedor.
    # `attempts` cuenta cada ejecución real, incluida la del reintento manual
    # (corrección de la auditoría: antes el contador quedaba plano).
    assert job.attempts == SETTINGS.wallet_job_max_attempts + 1
    assert job.manual_retries == 1
    passes = db_session.scalars(
        select(WalletPass).where(WalletPass.membership_id == membership.id)
    ).all()
    assert len(passes) == 1


def test_fallo_de_wallet_no_afecta_al_ledger(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    _patch_provider(monkeypatch, FailingProvider())
    membership = _membership(db_session)

    # Simula que la tarjeta ya tenía un pase emitido que hay que sincronizar.
    db_session.add(
        WalletPass(
            merchant_id=membership.merchant_id,
            membership_id=membership.id,
            provider="apple",
            status="issued",
            simulated=0,
        )
    )
    db_session.flush()

    resultado = ledger_service.earn(
        db_session,
        membership.id,
        membership.merchant_id,
        quantity=1,
        idempotency_key="visita-proveedor-caido",
        actor_user_id=None,
    )
    trabajos = wallet_service.update_passes_after_operation(db_session, membership, SETTINGS)

    db_session.expire_all()
    movimientos = db_session.scalars(
        select(LoyaltyTransaction).where(LoyaltyTransaction.membership_id == membership.id)
    ).all()
    assert resultado.membership.stamps == 1
    assert len(movimientos) == 1  # el sello está confirmado en el ledger
    # La sincronización fallida queda visible para reintentar, sin tocar saldo.
    assert len(trabajos) == 1
    assert trabajos[0].status in {JobStatus.RETRYING, JobStatus.FAILED}
