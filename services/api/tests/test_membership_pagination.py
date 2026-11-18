"""Paginación y contadores del listado de tarjetas (mejora de compra #4).

La cabecera de la pantalla de Clientes rotula totales reales de la base de
datos aunque solo se pinte una página: nada de contadores inventados en
cliente (§12.1, §13.2). El chip «Premio listo» usa el mismo filtro del
backend (`ready`), no un recorte local.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, enroll_verified, login
from .test_ledger import _membership, _world


def _enroll_more(client: TestClient, db_session: Session, email: str, name: str) -> None:
    enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        "club-del-cafe",
        {
            "email": email,
            "display_name": name,
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )


def test_paginacion_sin_solape_y_contadores_reales(client: TestClient, db_session: Session) -> None:
    """limit/offset reparten las tarjetas sin solape; los contadores son globales."""
    merchant_id, token, _ = _world(client, db_session)
    _enroll_more(client, db_session, "segundo@example.com", "Segundo Cliente")
    _enroll_more(client, db_session, "tercero@example.com", "Tercer Cliente")
    login(client, OWNER_EMAIL)
    url = f"/api/v1/merchants/{merchant_id}/memberships"

    primera = client.get(url, params={"limit": 2}).json()
    assert len(primera["items"]) == 2
    assert primera["total"] == 3
    assert primera["active"] == 3
    assert primera["suspended"] == 0
    assert primera["ready"] == 0

    segunda = client.get(url, params={"limit": 2, "offset": 2}).json()
    assert len(segunda["items"]) == 1
    assert segunda["total"] == 3
    # Sin solape ni saltos entre páginas (orden estable joined_at desc, id).
    assert {row["id"] for row in primera["items"]}.isdisjoint(row["id"] for row in segunda["items"])
    # La primera página es siempre la más reciente.
    assert primera["items"][0]["joined_at"] >= segunda["items"][0]["joined_at"]


def test_filtro_premio_listo_lo_cuenta_el_backend(client: TestClient, db_session: Session) -> None:
    """El chip «Premio listo» filtra y cuenta en servidor, no en cliente."""
    merchant_id, token, _ = _world(client, db_session)
    _enroll_more(client, db_session, "segundo@example.com", "Segundo Cliente")
    login(client, OWNER_EMAIL)
    url = f"/api/v1/merchants/{merchant_id}/memberships"

    # «Café gratis» cuesta 10 sellos: el primero llega, el segundo no.
    membership = _membership(db_session, token)
    login(client, "staff-a@example.com")
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"quantity": 11, "idempotency_key": "paginacion-ready-1"},
    )
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    filtrado = client.get(url, params={"ready": True}).json()
    assert filtrado["total"] == 1
    assert [row["id"] for row in filtrado["items"]] == [str(membership.id)]
    # La etiqueta del chip sigue siendo el recuento global: no cambia al
    # activar el propio filtro.
    assert filtrado["ready"] == 1

    # Límites duros: limit fuera de rango es un 422, no una página vacía.
    assert client.get(url, params={"limit": 0}).status_code == 422
    assert client.get(url, params={"limit": 101}).status_code == 422
    assert client.get(url, params={"offset": -1}).status_code == 422
