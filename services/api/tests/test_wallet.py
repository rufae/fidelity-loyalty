"""Pruebas de Wallet: simulado, proveedor sin configurar y trabajos (FASE 7/8)."""

import uuid

import pytest
from app.core.config import Settings, get_settings
from app.main import app
from app.models.members import Membership
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, STAFF_EMAIL, login
from .test_ledger import _membership, _world


def test_emision_simulada_queda_rotulada_como_simulada(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/wallet/issue"
    )

    assert response.status_code == 202, response.text
    payload = response.json()
    # §17.2: un pase simulado nunca puede confundirse con uno real.
    assert payload["simulated"] is True
    assert payload["provider"] == "simulated"
    assert payload["status"] == "issued"
    assert payload["job_status"] == "succeeded"


def test_proveedor_sin_configurar_no_rompe_y_deja_error_visible(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    apple_settings = Settings.model_validate(
        {**get_settings().model_dump(), "wallet_provider": "apple"}
    )
    app.dependency_overrides[get_settings] = lambda: apple_settings
    try:
        login(client, STAFF_EMAIL)
        response = client.post(
            f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/wallet/issue"
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_status"] == "failed"
    assert payload["last_error_code"] == "not_configured"
    # El mensaje orienta a la configuración, sin filtrar rutas ni secretos.
    assert "Pass Type ID" in payload["last_error_detail"]


def test_tras_acumular_se_programa_la_actualizacion(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    client.post(f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/wallet/issue")
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-con-wallet-1"},
    )

    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)  # el panel de trabajos es de administración
    jobs = client.get(f"/api/v1/merchants/{merchant_id}/wallet/jobs")

    assert jobs.status_code == 200
    types = [j["job_type"] for j in jobs.json()]
    assert "wallet.issue" in types
    assert "wallet.update" in types
    assert all(j["status"] == "succeeded" for j in jobs.json())


def test_el_rollback_de_wallet_no_reviente_el_ledger(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§6.1/§15: si el proveedor falla, el sello sigue quedando registrado."""
    from app.integrations.wallet.base import PassResult, ProviderStatus
    from app.integrations.wallet.simulated import SimulatedWalletProvider

    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    client.post(f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/wallet/issue")

    def roto(
        self: SimulatedWalletProvider,
        membership_id: uuid.UUID,
        public_token: str,
        context: object = None,
    ) -> PassResult:
        return PassResult(
            provider_object_id="",
            status=ProviderStatus.ERROR,
            simulated=True,
            detail="Proveedor caído (simulado para la prueba)",
        )

    monkeypatch.setattr(SimulatedWalletProvider, "update_pass", roto)
    respuesta = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-proveedor-caido"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["stamps"] == 1
    db_session.refresh(membership)
    assert membership.stamps == 1  # el ledger no se revierte
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)
    jobs = client.get(f"/api/v1/merchants/{merchant_id}/wallet/jobs").json()
    # Con reintentos (§15) el fallo recuperable queda en `retrying` y solo
    # pasa a `failed` (dead-letter) al agotar los intentos; lo importante es
    # que queda **visible** y que el ledger no se revirtió (assert de arriba).
    assert any(
        j["job_type"] == "wallet.update" and j["status"] in {"retrying", "failed"} for j in jobs
    )


def test_no_se_puede_emitir_de_otro_comercio(client: TestClient, db_session: Session) -> None:
    from .conftest import create_merchant_with_owner, create_user

    _, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    owner_b = create_user(db_session, "owner-b@example.com")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Bar B")
    db_session.commit()
    login(client, "owner-b@example.com")

    response = client.post(
        f"/api/v1/merchants/{merchant_b.id}/memberships/{membership.id}/wallet/issue"
    )

    assert response.status_code == 404
    assert db_session.query(Membership).count() == 1


def test_emision_es_idempotente_por_trabajo(client: TestClient, db_session: Session) -> None:
    """Reintentar la emisión no duplica pases: uno por membresía y proveedor."""
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/wallet/issue"

    client.post(url)
    client.post(url)
    passes = client.get(f"/api/v1/merchants/{merchant_id}/wallet/passes")

    assert len(passes.json()) == 1
