"""Modo puntos por importe (mejora de compra #9, §7.1 y §7.6).

- El programa se crea como `points` con una regla entera de puntos por
  euro; sin regla no se puede publicar.
- El importe lo teclea el personal (MVP sin TPV) y **el backend** calcula
  los puntos en Decimal con redondeo hacia abajo: el navegador nunca
  envía la cantidad a otorgar, y mezclar modos se rechaza sin registrar
  nada.
"""

from app.domain.roles import MerchantRole
from fastapi.testclient import TestClient
from httpx import Response
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
from .test_ledger import TERMS, _membership


def _points_world(
    client: TestClient,
    db_session: Session,
    *,
    rate: int | None = 2,
    reward_cost: int = 50,
) -> tuple[str, str, str, str]:
    """Comercio con programa de puntos (2 puntos/euro) y cliente dado de alta.

    Devuelve `(merchant_id, program_id, reward_id, public_token)`.
    """
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Pizzeria Puntos")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    login(client, OWNER_EMAIL)
    body: dict[str, object] = {
        "name": "Club por euros",
        "terms": "2 puntos por euro gastado. Canje desde 50 puntos.",
        "program_type": "points",
    }
    if rate is not None:
        body["points_per_euro"] = rate
    program = client.post(f"/api/v1/merchants/{merchant.id}/programs", json=body).json()
    reward = client.post(
        f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/rewards",
        json={"name": "Pizza gratis", "stamps_required": reward_cost},
    ).json()
    publicado = client.post(f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/publish")
    assert publicado.status_code == 200, publicado.text
    client.post("/api/v1/auth/logout")
    _, token = enroll_verified(
        client,
        db_session,
        merchant.slug,
        program["slug"],
        {
            "email": "cliente-puntos@example.com",
            "display_name": "Cliente Puntos",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    client.post("/api/v1/auth/logout")
    return str(merchant.id), str(program["id"]), str(reward["id"]), token


def _earn(
    client: TestClient,
    merchant_id: str,
    membership_id: str,
    body: dict[str, object],
) -> Response:
    login(client, STAFF_EMAIL)
    response: Response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json=body,
    )
    client.post("/api/v1/auth/logout")
    return response


def test_el_programa_de_puntos_se_crea_validado_y_se_publica_con_regla(
    client: TestClient, db_session: Session
) -> None:
    """`points` es un tipo válido; sin puntos/euro no se publica (§7.6)."""
    owner = create_user(db_session, OWNER_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Tienda Tipos")
    db_session.commit()
    login(client, OWNER_EMAIL)
    url = f"/api/v1/merchants/{merchant.id}/programs"

    # Tipo fuera de catálogo: 422, nunca un programa a medias.
    assert (
        client.post(url, json={"name": "Rarito", "terms": TERMS, "program_type": "vip"}).status_code
        == 422
    )

    sin_regla = client.post(
        url,
        json={"name": "Sin regla", "terms": TERMS, "program_type": "points"},
    ).json()
    assert sin_regla["program_type"] == "points"
    assert sin_regla["points_per_euro"] is None

    # Publicar sin regla se rechaza con un error accionable.
    fallo = client.post(f"{url}/{sin_regla['id']}/publish")
    assert fallo.status_code == 422
    assert fallo.json()["detail"]["code"] == "points_rule_required"

    # Con la regla, se publica.
    ok = client.patch(f"{url}/{sin_regla['id']}", json={"points_per_euro": 3})
    assert ok.status_code == 200 and ok.json()["points_per_euro"] == 3
    assert client.post(f"{url}/{sin_regla['id']}/publish").status_code == 200

    # Regla fuera de rango: 422 (nada de puntos negativos ni cero).
    assert (
        client.post(
            url,
            json={
                "name": "Cero",
                "terms": TERMS,
                "program_type": "points",
                "points_per_euro": 0,
            },
        ).status_code
        == 422
    )


def test_los_puntos_se_calculan_en_backend_con_redondeo_hacia_abajo(
    client: TestClient, db_session: Session
) -> None:
    """Navegador solo manda importe; puntos = floor(importe × regla)."""
    merchant_id, _, _, token = _points_world(client, db_session, rate=2)
    membership = _membership(db_session, token)

    # 12,50 € × 2 = 25 puntos exactos.
    ok = _earn(
        client,
        merchant_id,
        str(membership.id),
        {"amount": 12.5, "idempotency_key": "puntos-importe-1"},
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["quantity"] == 25
    assert ok.json()["stamps"] == 25

    # 0,05 € × 2 = 0,1 → redondea a 0 → se rechaza: no se registra nada.
    insuficiente = _earn(
        client,
        merchant_id,
        str(membership.id),
        {"amount": 0.05, "idempotency_key": "puntos-importe-2"},
    )
    assert insuficiente.status_code == 422
    assert insuficiente.json()["detail"]["code"] == "insufficient_amount"

    # Más de dos decimales: el importe no es un euro creíble (§7.6).
    fraccion = _earn(
        client,
        merchant_id,
        str(membership.id),
        {"amount": 12.345, "idempotency_key": "puntos-importe-3"},
    )
    assert fraccion.status_code == 422

    db_session.refresh(membership)
    assert membership.stamps == 25  # el rechazo no dejó saldo fantasma


def test_puntos_no_acepta_sellos_ni_omite_el_importe(
    client: TestClient, db_session: Session
) -> None:
    """En modo puntos solo vale el importe: sin mezclar modos (§7.6)."""
    merchant_id, _, _, token = _points_world(client, db_session)
    membership = _membership(db_session, token)

    con_sellos = _earn(
        client,
        merchant_id,
        str(membership.id),
        {"quantity": 2, "idempotency_key": "puntos-mezcla-1"},
    )
    assert con_sellos.status_code == 422
    assert con_sellos.json()["detail"]["code"] == "invalid_quantity"

    sin_importe = _earn(
        client,
        merchant_id,
        str(membership.id),
        {"idempotency_key": "puntos-mezcla-2"},
    )
    assert sin_importe.status_code == 422
    assert sin_importe.json()["detail"]["code"] == "amount_required"

    db_session.refresh(membership)
    assert membership.stamps == 0  # ningún rechazo dejó saldo fantasma


def test_los_sellos_no_admiten_importe(client: TestClient, db_session: Session) -> None:
    """Un programa de sellos rechaza el importe con un error claro (§7.6)."""
    from .test_ledger import _world

    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)

    con_importe = _earn(
        client,
        str(merchant_id),
        str(membership.id),
        {"amount": 5, "idempotency_key": "sellos-con-importe"},
    )
    assert con_importe.status_code == 422
    assert con_importe.json()["detail"]["code"] == "amount_not_allowed"


def test_el_canje_de_puntos_es_idempotente(client: TestClient, db_session: Session) -> None:
    """La misma venta repetida no duplica puntos ni el canje falla dos veces."""
    merchant_id, _, reward_id, token = _points_world(client, db_session, rate=2, reward_cost=50)
    membership = _membership(db_session, token)

    # Dos ventas de 25,00 € con la MISMA clave: solo se aplica una.
    venta = {"amount": 25.0, "idempotency_key": "puntos-idem-repetida"}
    primera = _earn(client, merchant_id, str(membership.id), venta)
    repetida = _earn(client, merchant_id, str(membership.id), venta)
    assert primera.status_code == 201 and repetida.status_code == 201
    assert repetida.json()["already_applied"] is True

    db_session.refresh(membership)
    assert membership.stamps == 50  # 25 × 2, sin duplicar

    # Con 50 puntos se canjea la recompensa (coste en puntos, §7.1).
    login(client, STAFF_EMAIL)
    canje = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "puntos-canje-1"},
    )
    assert canje.status_code == 201, canje.text
    db_session.refresh(membership)
    assert membership.stamps == 0


def test_el_alta_y_la_ficha_explican_la_regla_de_puntos(
    client: TestClient, db_session: Session
) -> None:
    """La página pública y el listado comunican tipo y regla (§7.6, §13.4)."""
    merchant_id, program_id, _, token = _points_world(client, db_session, rate=2)

    publico = client.get("/api/v1/public/programs/pizzeria-puntos/club-por-euros")
    assert publico.status_code == 200
    assert publico.json()["program_type"] == "points"
    assert publico.json()["points_per_euro"] == 2

    login(client, OWNER_EMAIL)
    listing = client.get(f"/api/v1/merchants/{merchant_id}/memberships")
    fila = next(
        row
        for row in listing.json()["items"]
        if row["id"] == str(_membership(db_session, token).id)
    )
    assert fila["program_type"] == "points"

    detalle = client.get(f"/api/v1/merchants/{merchant_id}/programs/{program_id}")
    assert detalle.json()["program_type"] == "points"
    assert detalle.json()["points_per_euro"] == 2
