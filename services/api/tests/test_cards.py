"""Pruebas de tarjeta web, QR e identificación en el mostrador (FASE 6)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import STAFF_EMAIL, login
from .test_ledger import _membership, _world


def test_qr_de_la_tarjeta_es_un_svg(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)

    response = client.get(f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/qr")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    # Un QR de verdad: suficiente estructura y sin datos personales (§5.2, §14.1).
    assert response.text.startswith("<?xml") or "<svg" in response.text
    assert "example.com" not in response.text
    # El contenido del QR es la URL ABSOLUTA de la tarjeta (regresión real:
    # un QR con ruta relativa solo muestra texto al escanearlo, §14.1).
    content = response.headers["X-QR-Content"]
    assert content.startswith("http")
    assert content.endswith(f"/card/{membership.public_token}")


def test_qr_de_la_tarjeta_publica_es_url_absoluta(client: TestClient, db_session: Session) -> None:
    _, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)

    response = client.get(f"/api/v1/public/memberships/{membership.public_token}/qr")

    assert response.status_code == 200
    content = response.headers["X-QR-Content"]
    assert content.startswith("http")
    assert content.endswith(f"/card/{membership.public_token}")


def test_lookup_por_codigo_dentro_del_comercio(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/lookup", json={"token": token}
    )

    assert response.status_code == 200, response.text
    assert response.json()["public_token"] == token


def test_lookup_no_cruza_comercios(client: TestClient, db_session: Session) -> None:
    from .conftest import create_merchant_with_owner, create_user

    _, token, _ = _world(client, db_session)
    owner_b = create_user(db_session, "owner-b@example.com")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Bar B")
    db_session.commit()
    login(client, "owner-b@example.com")

    ajeno = client.post(
        f"/api/v1/merchants/{merchant_b.id}/memberships/lookup", json={"token": token}
    )
    inexistente = client.post(
        f"/api/v1/merchants/{merchant_b.id}/memberships/lookup",
        json={"token": "f" * 64},
    )

    # Mismo código en ambos casos: no se puede adivinar si un token existe (§8.2).
    assert ajeno.status_code == inexistente.status_code == 404


def test_staff_no_obtiene_el_qr_de_un_comercio_ajeno(
    client: TestClient, db_session: Session
) -> None:
    from .conftest import create_merchant_with_owner, create_user

    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    owner_b = create_user(db_session, "owner-b@example.com")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Bar B")
    db_session.commit()
    login(client, "owner-b@example.com")

    response = client.get(f"/api/v1/merchants/{merchant_b.id}/memberships/{membership.id}/qr")

    assert response.status_code == 404
