"""Búsqueda de clientes por nombre/correo en el mostrador (§13.5).

Cuando el cliente no tiene el móvil a mano, el personal puede localizar su
tarjeta por nombre o correo. Está permitida a roles operativos porque es una
función de mostrador, y **queda registrada en la auditoría** (sin PII: solo
el hash del término).
"""

from uuid import uuid4

from app.models.audit import AuditEvent
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, STAFF_EMAIL, create_merchant_with_owner, create_user, login
from .test_ledger import _world


def test_staff_busca_por_nombre_y_por_correo(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)

    por_nombre = client.get(
        f"/api/v1/merchants/{merchant_id}/memberships/search", params={"q": "Cliente de"}
    )
    assert por_nombre.status_code == 200, por_nombre.text
    assert por_nombre.json()[0]["member_name"] == "Cliente de Prueba"
    assert por_nombre.json()[0]["public_token"] == token

    por_correo = client.get(
        f"/api/v1/merchants/{merchant_id}/memberships/search", params={"q": "cliente@EXAMPLE"}
    )
    assert por_correo.status_code == 200
    assert por_correo.json()[0]["member_email"] == "cliente@example.com"


def test_la_busqueda_queda_registrada_en_auditoria_sin_pii(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)
    client.get(
        f"/api/v1/merchants/{merchant_id}/memberships/search", params={"q": "Cliente de Prueba"}
    )

    db_session.commit()
    db_session.expire_all()
    event = db_session.scalars(
        select(AuditEvent).where(AuditEvent.action == "member.searched")
    ).first()
    assert event is not None, "la búsqueda de clientes debe quedar auditada (§13.5)"
    assert event.actor_id is not None
    # Ni el término ni el email en claro: solo su hash (§16.6).
    assert "Cliente de Prueba" not in str(event.metadata_json)
    assert "term_hash" in str(event.metadata_json)


def test_el_termino_debe_tener_almenos_2_caracteres(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)

    response = client.get(f"/api/v1/merchants/{merchant_id}/memberships/search", params={"q": "c"})

    assert response.status_code == 422


def test_la_busqueda_no_atraviesa_comercios(client: TestClient, db_session: Session) -> None:
    merchant_a, _, _ = _world(client, db_session)
    owner_b = create_user(db_session, "owner-b@example.com")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Cafetería B")
    db_session.commit()
    login(client, STAFF_EMAIL)  # staff del comercio A

    # El staff de A no puede buscar en el comercio B (404, sin enumerar, §8.2).
    ajena = client.get(
        f"/api/v1/merchants/{merchant_b.id}/memberships/search", params={"q": "Cliente"}
    )
    assert ajena.status_code == 404

    # La búsqueda de A solo devuelve tarjetas de A.
    propia = client.get(
        f"/api/v1/merchants/{merchant_a}/memberships/search", params={"q": "Cliente de Prueba"}
    )
    assert propia.status_code == 200
    assert len(propia.json()) == 1


def test_el_listado_de_clientes_filtra_por_nombre_o_correo(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, token, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    response = client.get(
        f"/api/v1/merchants/{merchant_id}/memberships", params={"q": "cliente@example.com"}
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["public_token"] == token
    assert rows[0]["member_name"] == "Cliente de Prueba"

    vacio = client.get(f"/api/v1/merchants/{merchant_id}/memberships", params={"q": "nadie-asi"})
    assert vacio.json() == []


def test_el_lookup_de_mostrador_incluye_la_identidad_del_cliente(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, token, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/lookup", json={"token": token}
    )

    assert response.status_code == 200
    assert response.json()["member_name"] == "Cliente de Prueba"
    assert response.json()["member_email"] == "cliente@example.com"
    # El programa viaja con la tarjeta: el mostrador sabe qué promoción es.
    assert response.json()["program_name"] == "Club del Café"
    # El código del QR no contiene PII (§5.2): sigue siendo opaco.
    assert response.json()["public_token"] == token


def test_las_tarjetas_del_cliente_cubren_todos_sus_programas(
    client: TestClient, db_session: Session
) -> None:
    """Un cliente en dos programas (5 cafés y 3 menús) tiene dos tarjetas."""
    merchant_id, token, _ = _world(client, db_session)

    # Segundo programa del mismo comercio, publicado.
    login(client, OWNER_EMAIL)
    second = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Amigos del Menú", "terms": "3 menús, medio menú gratis"},
    ).json()
    client.post(f"/api/v1/merchants/{merchant_id}/programs/{second['id']}/publish")
    client.post("/api/v1/auth/logout")

    # El mismo email se inscribe en el segundo programa: reutiliza el cliente
    # y crea una segunda membresía (§7.6 del alta).
    enroll = client.post(
        f"/api/v1/public/programs/cafeteria-a/{second['slug']}/enroll",
        json={
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    assert enroll.status_code == 201, enroll.text

    # El personal ve las dos tarjetas y puede elegir la promoción correcta.
    login(client, STAFF_EMAIL)
    lookup = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/lookup", json={"token": token}
    ).json()
    cards = client.get(f"/api/v1/merchants/{merchant_id}/members/{lookup['member_id']}/cards")

    assert cards.status_code == 200
    programs = {row["program_name"] for row in cards.json()}
    assert programs == {"Club del Café", "Amigos del Menú"}
    assert all(row["member_name"] == "Cliente de Prueba" for row in cards.json())


def test_las_tarjetas_de_un_cliente_desconocido_responden_404(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)

    response = client.get(f"/api/v1/merchants/{merchant_id}/members/{uuid4()}/cards")

    assert response.status_code == 404


def test_sin_sesion_no_se_puede_buscar(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    client.post("/api/v1/auth/logout")

    response = client.get(
        f"/api/v1/merchants/{merchant_id}/memberships/search", params={"q": "Cliente"}
    )

    assert response.status_code == 401
