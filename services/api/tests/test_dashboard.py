"""Pruebas de analítica y exportación (FASE 11)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, STAFF_EMAIL, login
from .test_ledger import _membership, _world


def test_resumen_refleja_operaciones_reales(client: TestClient, db_session: Session) -> None:
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    for i in range(10):
        client.post(earn_url, json={"idempotency_key": f"visita-{i}"})
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "canje-resumen-1"},
    )
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    resumen = client.get(f"/api/v1/merchants/{merchant_id}/dashboard/summary")

    assert resumen.status_code == 200
    datos = resumen.json()
    assert datos["members_total"] == 1
    assert datos["memberships_active"] == 1
    assert datos["stamps_granted"] == 10
    assert datos["stamps_redeemed"] == 10
    assert datos["redemptions"] == 1
    # §4.4: el nombre de la métrica nunca sugiere reseñas publicadas.
    assert datos["review_link_clicks"] == 0


def test_serie_diaria_y_periodo(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn",
        json={"idempotency_key": "visita-serie-1"},
    )
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    serie = client.get(f"/api/v1/merchants/{merchant_id}/dashboard/loyalty?period=7")

    assert serie.status_code == 200
    assert serie.json()["period_days"] == 7
    assert any(punto["transaction_type"] == "earn" for punto in serie.json()["series"])


def test_staff_no_ve_analitica(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)
    assert client.get(f"/api/v1/merchants/{merchant_id}/dashboard/summary").status_code == 404


def test_export_csv_sin_tokens_ni_ids(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, OWNER_EMAIL)

    export = client.get(f"/api/v1/merchants/{merchant_id}/export/members.csv")

    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    # §21.2: datos propios y mínimos; nunca el token de la tarjeta.
    assert token not in export.text
    assert str(membership.id) not in export.text
