"""Pruebas del ledger: idempotencia, doble gasto, permisos y reconciliación (FASE 5)."""

import uuid
from typing import Any

from app.domain.roles import MerchantRole
from app.models.ledger import LoyaltyTransaction, RewardRedemption
from app.models.members import Membership
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_EMAIL,
    STAFF_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    enroll_verified,
    login,
)

TERMS = "1 sello por visita. Canje desde 10 sellos."


def _world(client: TestClient, db_session: Session) -> tuple[uuid.UUID, str, str]:
    """Comercio con programa activo (10 sellos = café) y un miembro registrado."""
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Cafetería A")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant.id}/programs",
        json={"name": "Club del Café", "terms": TERMS},
    ).json()
    reward = client.post(
        f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/rewards",
        json={"name": "Café gratis", "stamps_required": 10},
    ).json()
    client.post(f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/publish")
    client.post("/api/v1/auth/logout")
    _, token = enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        program["slug"],
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    client.post("/api/v1/auth/logout")
    assert merchant.id is not None
    return merchant.id, token, reward["id"]


def _membership(db_session: Session, token: str) -> Membership:
    return db_session.query(Membership).filter(Membership.public_token == token).one()


def test_acumular_sellos_y_reconciliar_con_el_ledger(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"quantity": 1, "idempotency_key": "visita-1-cliente-1"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["stamps"] == 1
    assert response.json()["transaction_type"] == "earn"

    db_session.refresh(membership)
    total_ledger = sum(t.quantity for t in db_session.query(LoyaltyTransaction).all())
    assert membership.stamps == total_ledger == 1


def test_idempotencia_no_duplica_sellos(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    body = {"quantity": 1, "idempotency_key": "misma-clave-visita"}

    primera = client.post(url, json=body)
    segunda = client.post(url, json=body)

    assert primera.status_code == segunda.status_code == 201
    assert segunda.json()["already_applied"] is True
    db_session.refresh(membership)
    assert membership.stamps == 1
    assert db_session.query(LoyaltyTransaction).count() == 1


def test_no_puede_canjear_sin_sellos_suficientes(client: TestClient, db_session: Session) -> None:
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "canje-temprano-1"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "insufficient_stamps"
    db_session.refresh(membership)
    assert membership.stamps == 0


def test_canje_exitoso_y_no_doble_gasto(client: TestClient, db_session: Session) -> None:
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    for i in range(10):
        client.post(earn_url, json={"quantity": 1, "idempotency_key": f"visita-{i}"})

    redeem_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem"
    body = {"reward_id": reward_id, "idempotency_key": "canje-cafe-1"}
    primera = client.post(redeem_url, json=body)
    repetida = client.post(redeem_url, json=body)

    assert primera.status_code == 201, primera.text
    assert primera.json()["stamps"] == 0
    assert repetida.json()["already_applied"] is True
    # Un solo canje real (§7.5: una recompensa no se canjea más de una vez).
    assert db_session.query(RewardRedemption).count() == 1
    db_session.refresh(membership)
    assert membership.stamps == 0


def test_no_se_puede_acumular_en_programa_pausado(client: TestClient, db_session: Session) -> None:
    from app.models.loyalty import LoyaltyProgram

    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, OWNER_EMAIL)
    program = (
        db_session.query(LoyaltyProgram).filter(LoyaltyProgram.merchant_id == merchant_id).one()
    )
    client.post(f"/api/v1/merchants/{merchant_id}/programs/{program.id}/pause")
    client.post("/api/v1/auth/logout")
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-en-pausa"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "program_not_active"


def test_staff_no_puede_ajustar(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/adjust",
        json={"delta": -3, "reason": "corrección"},
    )

    assert response.status_code == 404  # sin permiso: mismo código que inexistente


def test_ajuste_del_dueno_con_motivo(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-ajuste-1"},
    )
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    negativo = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/adjust",
        json={"delta": -5, "reason": "devolución"},
    )
    valido = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/adjust",
        json={"delta": 2, "reason": "buena fe corregida"},
    )

    assert negativo.status_code == 409  # no puede dejarla en negativo
    assert valido.status_code == 201
    db_session.refresh(membership)
    assert membership.stamps == 3
    ajustes = [
        t for t in db_session.query(LoyaltyTransaction).all() if t.transaction_type == "adjustment"
    ]
    assert ajustes[0].reason == "buena fe corregida"


def test_no_operar_membresias_de_otro_comercio(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    # Segundo comercio con su propio owner.
    owner_b = create_user(db_session, "owner-b@example.com")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Bar B")
    db_session.commit()
    login(client, "owner-b@example.com")

    lectura = client.get(f"/api/v1/merchants/{merchant_b.id}/memberships/{membership.id}")
    escritura = client.post(
        f"/api/v1/merchants/{merchant_b.id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "intrusion-intento-1"},
    )

    assert lectura.status_code == 404
    assert escritura.status_code == 404
    db_session.refresh(membership)
    assert membership.stamps == 0  # sin efecto


def test_staff_no_ajusta_ni_elimina_historial(client: TestClient, db_session: Session) -> None:
    """El historial es inmutable: no existe endpoint de borrado (§7.3)."""
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-inmutable-1"},
    )

    historial = client.get(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/transactions"
    )

    assert historial.status_code == 200
    assert len(historial.json()) == 1
    assert client.delete(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/transactions"
    ).status_code in {404, 405}


def test_ajuste_fuera_de_rango(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, OWNER_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/adjust",
        json={"delta": 0, "reason": "nulo"},
    )

    assert response.status_code == 422


def test_operaciones_quedan_audiadas(client: TestClient, db_session: Session) -> None:
    from app.models.audit import AuditEvent

    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-auditoria-1"},
    )

    actions: set[Any] = {e.action for e in db_session.query(AuditEvent).all()}
    assert "loyalty.earn" in actions
