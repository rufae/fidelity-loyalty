"""Ciclo de vida de la membresía y la tarjeta (ADR-0005, tasks2 §3 y §10).

Cubre: transiciones válidas e inválidas, bloqueo inmediato de earn/redeem en
estados no activos, aislamiento entre comercios, roles, supresión que
anonimiza **conservando el ledger** y auditoría de cada cambio.
"""

import uuid
from typing import cast

from app.domain.roles import MerchantRole
from app.models.audit import AuditEvent
from app.models.ledger import LoyaltyTransaction
from app.models.members import Member, Membership
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_B_EMAIL,
    OWNER_EMAIL,
    PASSWORD,
    STAFF_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    enroll_verified,
    login,
)

TERMS = "1 sello por visita."
ENROLL = {
    "email": "cliente@example.com",
    "display_name": "Cliente de Prueba",
    "privacy_notice_version": 1,
    "accepted_terms_version": 1,
}


def _world(client: TestClient, db_session: Session) -> tuple[uuid.UUID, str, str]:
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Cafetería A")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant.id}/programs",
        json={"name": "Club", "terms": TERMS},
    ).json()
    client.post(
        f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/rewards",
        json={"name": "Café gratis", "stamps_required": 2},
    )
    client.post(f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/publish")
    client.post("/api/v1/auth/logout")
    _, token = enroll_verified(client, db_session, "cafeteria-a", program["slug"], ENROLL)
    assert merchant.id is not None
    return merchant.id, program["slug"], token


def _membership_id(db_session: Session, token: str) -> uuid.UUID:
    membership = db_session.scalar(select(Membership).where(Membership.public_token == token))
    assert membership is not None and membership.id is not None
    return membership.id


def _action(
    client: TestClient,
    merchant_id: uuid.UUID,
    membership_id: uuid.UUID,
    action: str,
    *,
    reason: str | None = None,
) -> Response:
    return cast(
        "Response",
        client.post(
            f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/{action}",
            json={"reason": reason} if reason else {},
        ),
    )


def test_suspender_bloquea_operaciones_y_reactiva_las_restaura(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, OWNER_EMAIL)

    suspendida = _action(client, merchant_id, membership_id, "suspend", reason="tarjeta perdida")
    assert suspendida.status_code == 200
    assert suspendida.json()["status"] == "suspended"
    assert suspendida.json()["status_reason"] == "tarjeta perdida"

    earn = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-suspendida"},
    )
    assert earn.status_code == 409
    assert earn.json()["detail"]["code"] == "membership_suspended"

    reactivada = _action(client, merchant_id, membership_id, "reactivate")
    assert reactivada.status_code == 200 and reactivada.json()["status"] == "active"
    ok = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-reactivada"},
    )
    assert ok.status_code == 201 and ok.json()["stamps"] == 1


def test_revocar_es_definitivo(client: TestClient, db_session: Session) -> None:
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, OWNER_EMAIL)

    revocada = _action(client, merchant_id, membership_id, "revoke", reason="baja del cliente")
    assert revocada.status_code == 200 and revocada.json()["status"] == "revoked"

    earn = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-revocada"},
    )
    assert earn.status_code == 409
    assert earn.json()["detail"]["code"] == "membership_revoked"

    # Una revocada no se reactiva: transición inválida (ADR-0005).
    reactivar = _action(client, merchant_id, membership_id, "reactivate")
    assert reactivar.status_code == 409
    assert reactivar.json()["detail"]["code"] == "invalid_status_transition"


def test_transiciones_invalidas_se_rechazan(client: TestClient, db_session: Session) -> None:
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, OWNER_EMAIL)

    repetida = _action(client, merchant_id, membership_id, "suspend")
    assert repetida.status_code == 200
    otra_vez = _action(client, merchant_id, membership_id, "suspend")
    assert otra_vez.status_code == 409
    assert otra_vez.json()["detail"]["code"] == "invalid_status_transition"

    # Revocar una suspendida sí está permitido; revocar dos veces no.
    assert _action(client, merchant_id, membership_id, "revoke").status_code == 200
    assert _action(client, merchant_id, membership_id, "revoke").status_code == 409


def test_supresion_anonimiza_y_conserva_el_ledger(client: TestClient, db_session: Session) -> None:
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, OWNER_EMAIL)
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-antes-de-borrar"},
    )
    movimientos_antes = len(
        db_session.scalars(
            select(LoyaltyTransaction).where(LoyaltyTransaction.membership_id == membership_id)
        ).all()
    )

    solicitud = _action(client, merchant_id, membership_id, "request-deletion", reason="RGPD")
    assert solicitud.status_code == 200
    assert solicitud.json()["status"] == "deletion_pending"
    assert solicitud.json()["deletion_requested_at"]

    # La solicitud pendiente sigue visible en la lista para poder completarla.
    pendientes = client.get(f"/api/v1/merchants/{merchant_id}/memberships").json()
    assert [row["status"] for row in pendientes] == ["deletion_pending"]

    anonimizada = _action(client, merchant_id, membership_id, "anonymize")
    assert anonimizada.status_code == 200 and anonimizada.json()["status"] == "anonymized"

    db_session.expire_all()
    membership = db_session.get(Membership, membership_id)
    assert membership is not None and membership.anonymized_at is not None
    member = db_session.get(Member, membership.member_id)
    assert member is not None
    assert member.email is None and member.display_name is None
    assert member.anonymized_at is not None

    # El ledger se conserva (§7.3): nada de DELETE CASCADE.
    movimientos_despues = db_session.scalars(
        select(LoyaltyTransaction).where(LoyaltyTransaction.membership_id == membership_id)
    ).all()
    assert len(movimientos_despues) == movimientos_antes

    # Y la tarjeta ya no se puede consultar ni operar.
    assert client.get(f"/api/v1/public/memberships/{token}").status_code == 403
    earn = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-tras-borrar"},
    )
    assert earn.status_code == 403


def test_eliminar_en_un_paso_y_desaparece_de_las_listas(
    client: TestClient, db_session: Session
) -> None:
    """«Eliminar cliente» del panel ejecuta la supresión directamente
    (enmienda ADR-0005) y el cliente borrado deja de listarse (§9.5)."""
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, OWNER_EMAIL)
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-eliminar-directo"},
    )
    movimientos_antes = len(
        db_session.scalars(
            select(LoyaltyTransaction).where(LoyaltyTransaction.membership_id == membership_id)
        ).all()
    )

    # Directo desde `active`, sin pasar por `deletion_pending`.
    eliminada = _action(client, merchant_id, membership_id, "anonymize")
    assert eliminada.status_code == 200
    assert eliminada.json()["status"] == "anonymized"

    db_session.expire_all()
    membership = db_session.get(Membership, membership_id)
    assert membership is not None and membership.anonymized_at is not None
    member = db_session.get(Member, membership.member_id)
    assert member is not None
    assert member.email is None and member.display_name is None
    assert member.anonymized_at is not None

    # El ledger se conserva (§7.3).
    movimientos_despues = db_session.scalars(
        select(LoyaltyTransaction).where(LoyaltyTransaction.membership_id == membership_id)
    ).all()
    assert len(movimientos_despues) == movimientos_antes

    # El cliente eliminado ya no aparece en las listas del comercio.
    assert client.get(f"/api/v1/merchants/{merchant_id}/memberships").json() == []
    assert client.get(f"/api/v1/merchants/{merchant_id}/members").json() == []


def test_ciclo_de_vida_aislado_entre_comercios(client: TestClient, db_session: Session) -> None:
    merchant_a, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    owner_b = create_user(db_session, OWNER_B_EMAIL, password=PASSWORD)
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Cafetería B")
    db_session.commit()

    login(client, OWNER_B_EMAIL)
    ajena = _action(client, merchant_b.id, membership_id, "suspend")
    assert ajena.status_code == 404  # igual que si no existiera (§8.2)

    login(client, OWNER_EMAIL)
    propia = _action(client, merchant_a, membership_id, "suspend")
    assert propia.status_code == 200


def test_staff_no_gestiona_el_ciclo_de_vida(client: TestClient, db_session: Session) -> None:
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, STAFF_EMAIL)

    respuesta = _action(client, merchant_id, membership_id, "revoke")
    assert respuesta.status_code in (403, 404)
    # El personal sí puede operar sellos (eso ya está cubierto en test_ledger).
    earn = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"idempotency_key": "k-staff-operativo"},
    )
    assert earn.status_code == 201


def test_cada_cambio_de_estado_queda_auditado(client: TestClient, db_session: Session) -> None:
    merchant_id, _slug, token = _world(client, db_session)
    membership_id = _membership_id(db_session, token)
    login(client, OWNER_EMAIL)
    _action(client, merchant_id, membership_id, "suspend", reason="prueba de auditoría")
    db_session.expire_all()

    acciones = {
        e.action
        for e in db_session.scalars(select(AuditEvent)).all()
        if e.entity_id == str(membership_id)
    }
    assert "membership.suspended" in acciones
