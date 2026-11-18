"""«Premio listo» y «Altas de hoy» (mejoras de compra #1, #2, #3).

- La insignia «Premio listo» se deriva del ledger y del catálogo activo del
  programa: el mostrador nunca inventa progresos.
- Las altas de hoy son la señal del puente mostrador: el personal ve quién se
  registró hoy en su zona horaria y puede darle el primer sello al momento,
  sin notificaciones push (una tienda con tráfico no vive de avisos).
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, STAFF_EMAIL, login
from .test_ledger import _membership, _world


def test_premio_listo_en_la_ficha(client: TestClient, db_session: Session) -> None:
    """Con sellos suficientes, la membresía marca `reward_ready` con el premio."""
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    # «Café gratis» cuesta 10 sellos: uno de más para cruzar el umbral.
    client.post(earn_url, json={"quantity": 11, "idempotency_key": "ready-0001"})
    # El listado es de administración (§13.5); el staff solo opera tarjetas.
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    listing = client.get(f"/api/v1/merchants/{merchant_id}/memberships")
    row = next(row for row in listing.json()["items"] if row["id"] == str(membership.id))
    assert row["reward_ready"] is True
    assert row["next_reward_remaining"] == 0
    assert row["next_reward_name"] == "Café gratis"

    # Punto intermedio: sin premio listo, pero con la cuenta atrás visible.
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "ready-canje-01"},
    )
    listing = client.get(f"/api/v1/merchants/{merchant_id}/memberships")
    row = next(row for row in listing.json()["items"] if row["id"] == str(membership.id))
    assert row["reward_ready"] is False
    # Tras el canje quedan 1 de 10: faltan 9 sellos para volver a alcanzarlo.
    assert row["next_reward_remaining"] == 9
    assert row["next_reward_name"] == "Café gratis"


def test_premio_listo_ignora_recompensas_inactivas(client: TestClient, db_session: Session) -> None:
    """Una recompensa archivada no puede hacer pasar a nadie por «premio listo»."""
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, OWNER_EMAIL)
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    client.post(earn_url, json={"quantity": 10, "idempotency_key": "inactiva-01"})
    # El owner archiva la recompensa (el catálogo deja de ofrecerla).
    client.patch(
        f"/api/v1/merchants/{merchant_id}/programs/{membership.program_id}/rewards/{reward_id}",
        json={"status": "inactive"},
    )
    listing = client.get(f"/api/v1/merchants/{merchant_id}/memberships")
    row = next(row for row in listing.json()["items"] if row["id"] == str(membership.id))
    assert row["reward_ready"] is False


def test_altas_de_hoy_para_el_mostrador(client: TestClient, db_session: Session) -> None:
    """El staff ve las altas del día, con nombre mínimo y sin PII extra."""
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)

    listing = client.get(f"/api/v1/merchants/{merchant_id}/enrollments/today")
    assert listing.status_code == 200, listing.text
    rows = listing.json()
    row = next(row for row in rows if row["id"] == str(membership.id))
    assert row["member_name"] == "Cliente de Prueba"
    assert row["program_name"] == "Club del Café"
    # El correo no viaja a esta lista del mostrador: identidad mínima.
    assert "member_email" not in row or row["member_email"] in (None, "")


def test_altas_de_hoy_solo_el_dia_local(client: TestClient, db_session: Session) -> None:
    """Un alta de ayer (UTC desplazado) no aparece en «hoy» del comercio."""
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    # El alta de la factura es de hoy; la dejamos fuera del día empujándola atrás.
    from datetime import UTC, datetime, timedelta

    membership.joined_at = datetime.now(UTC) - timedelta(days=3)
    db_session.commit()

    login(client, STAFF_EMAIL)
    rows = client.get(f"/api/v1/merchants/{merchant_id}/enrollments/today").json()
    assert all(row["id"] != str(membership.id) for row in rows)


def test_altas_de_hoy_otro_comercio_404(client: TestClient, db_session: Session) -> None:
    """El §8.2: otro comercio no ve las altas de este."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    # Un id de comercio inventado responde 404, igual que en el resto.
    import uuid as uuid_module

    fake_id = str(uuid_module.uuid4())
    assert client.get(f"/api/v1/merchants/{fake_id}/enrollments/today").status_code == 404
