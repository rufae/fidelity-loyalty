"""Pruebas de analítica y exportación (FASE 11)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_EMAIL,
    STAFF_EMAIL,
    create_merchant_with_owner,
    create_user,
    enroll_verified,
    login,
)
from .test_ledger import TERMS, _membership, _world


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


def test_cierre_del_dia_refleja_lo_de_hoy(client: TestClient, db_session: Session) -> None:
    """El resumen del día (§13.2) cuenta lo del día, en la zona del comercio."""
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    client.post(earn_url, json={"quantity": 10, "idempotency_key": "hoy-earn-1"})
    client.post(earn_url, json={"idempotency_key": "hoy-earn-2"})
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "hoy-canje-1"},
    )
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    today = client.get(f"/api/v1/merchants/{merchant_id}/dashboard/today")

    assert today.status_code == 200
    datos = today.json()
    # Fecha local del comercio (§24.2), no el UTC bruto del ledger.
    assert datos["local_date"] and len(datos["local_date"]) == 10
    assert datos["enrolled_today"] == 1
    assert datos["stamps_today"] == 11
    assert datos["redeemed_stamps_today"] == 10
    assert datos["redemptions_today"] == 1


def test_staff_no_ve_analitica(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)
    assert client.get(f"/api/v1/merchants/{merchant_id}/dashboard/summary").status_code == 404


def test_staff_no_ve_el_cierre_del_dia(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)
    assert client.get(f"/api/v1/merchants/{merchant_id}/dashboard/today").status_code == 404


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


def test_export_transacciones_csv(client: TestClient, db_session: Session) -> None:
    """El CSV de movimientos refleja el ledger y no filtra datos personales."""
    merchant_id, token, reward_id = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, STAFF_EMAIL)
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/earn"
    client.post(earn_url, json={"quantity": 10, "idempotency_key": "csv-earn-1"})
    client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "csv-canje-1"},
    )
    client.post("/api/v1/auth/logout")
    login(client, OWNER_EMAIL)

    export = client.get(f"/api/v1/merchants/{merchant_id}/export/transactions.csv")

    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    # El token opaco es el identificador correcto en este CSV (§21.2): la
    # tarjeta es la entidad trazable, nunca el email ni el nombre del cliente.
    assert token in export.text
    assert "Cliente de Prueba" not in export.text
    assert "cliente@example.com" not in export.text
    assert "earn" in export.text
    assert "redeem" in export.text
    assert "Club del Café" in export.text

    # El staff no exporta (igual que la analítica).
    client.post("/api/v1/auth/logout")
    login(client, STAFF_EMAIL)
    assert client.get(f"/api/v1/merchants/{merchant_id}/export/transactions.csv").status_code == 404


def test_editar_cliente_nombre_y_correo(client: TestClient, db_session: Session) -> None:
    """Edición mínima (decisión de compra #9): el correo cambia a sin verificar."""
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, OWNER_EMAIL)

    response = client.patch(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}",
        json={"display_name": "Nombre Corregido", "email": "nuevo@example.com"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["member_name"] == "Nombre Corregido"
    assert data["member_email"] == "nuevo@example.com"

    # El correo nuevo no hereda la verificación del anterior (ADR-0006).
    db_session.expire_all()
    from app.models.members import Member

    member = db_session.query(Member).filter_by(id=membership.member_id).one()
    assert member.email_verified_at is None

    # Correo duplicado en el comercio → 409 legible.
    other = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships",
        json={
            "program_id": str(membership.program_id),
            "display_name": "Otra Persona",
            "email": "otra@example.com",
            "accepted_terms_version": 1,
            "privacy_notice_version": 1,
        },
    ).json()
    other_id = other["membership"]["id"]
    dup = client.patch(
        f"/api/v1/merchants/{merchant_id}/memberships/{other_id}",
        json={"email": "nuevo@example.com"},
    )
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "email_taken"


def test_editar_cliente_no_toca_membresia_ajena(client: TestClient, db_session: Session) -> None:
    """El §8.2: la membresía de otro comercio responde 404, no 403."""
    merchant_id, token, _ = _world(client, db_session)
    membership = _membership(db_session, token)
    login(client, OWNER_EMAIL)

    # Otro comercio con su propio propietario (los emails de usuarios son únicos).
    other_owner = create_user(db_session, "owner-segundo@example.com")
    other_merchant = create_merchant_with_owner(db_session, other_owner, name="Cafetería B")
    login(client, "owner-segundo@example.com")
    other_program = client.post(
        f"/api/v1/merchants/{other_merchant.id}/programs",
        json={"name": "Programa Ajeno", "terms": TERMS},
    ).json()
    client.post(f"/api/v1/merchants/{other_merchant.id}/programs/{other_program['id']}/publish")
    client.post(
        f"/api/v1/merchants/{other_merchant.id}/memberships",
        json={
            "program_id": other_program["id"],
            "display_name": "Cliente Ajeno",
            "email": "ajeno@example.com",
            "accepted_terms_version": 1,
            "privacy_notice_version": 1,
        },
    )
    from app.models.members import Membership as MembershipModel

    other = (
        db_session.query(MembershipModel)
        .filter(MembershipModel.merchant_id == other_merchant.id)
        .one()
    )

    response = client.patch(
        f"/api/v1/merchants/{other_merchant.id}/memberships/{membership.id}",
        json={"display_name": "No Debe Pasar"},
    )
    assert response.status_code == 404

    # Un comercio no ve la membresía ajena con su propio id tampoco.
    login(client, OWNER_EMAIL)
    wrong_scope = client.patch(
        f"/api/v1/merchants/{merchant_id}/memberships/{other.id}",
        json={"display_name": "Tampoco"},
    )
    assert wrong_scope.status_code == 404


def test_checklist_de_onboarding_avanza_hasta_el_primer_cliente(
    client: TestClient, db_session: Session
) -> None:
    """El Resumen muestra los primeros pasos reales del comercio nuevo (§13.2).

    Cada paso refleja el estado de la base de datos; en cuanto las cuatro
    puertas están cerradas, `completed` permite ocultar el checklist.
    """
    owner = create_user(db_session, OWNER_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Tostador Onboarding")
    db_session.commit()
    login(client, OWNER_EMAIL)
    url = f"/api/v1/merchants/{merchant.id}/dashboard/onboarding"

    inicial = client.get(url)
    assert inicial.status_code == 200
    assert inicial.json() == {
        "program_ready": False,
        "store_ready": False,
        "qr_ready": False,
        "first_member": False,
        "completed": False,
    }

    # 1) Programa publicado con recompensa activa.
    program = client.post(
        f"/api/v1/merchants/{merchant.id}/programs",
        json={"name": "Club del Tostador", "terms": TERMS},
    ).json()
    client.post(
        f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/rewards",
        json={"name": "Café gratis", "stamps_required": 10},
    )
    client.post(f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/publish")

    parcial = client.get(url).json()
    assert parcial["program_ready"] is True
    assert parcial["store_ready"] is False
    assert parcial["completed"] is False

    # 2) Tienda registrada y 3) QR de alta activo.
    assert (
        client.post(
            f"/api/v1/merchants/{merchant.id}/locations",
            json={"name": "Sede Centro"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/merchants/{merchant.id}/nfc-tags",
            json={
                "tag_type": "loyalty_signup",
                "label": "Mostrador",
                "program_id": program["id"],
            },
        ).status_code
        == 201
    )

    # 4) Primer cliente dado de alta por el propio recorrido público.
    client.post("/api/v1/auth/logout")
    enroll_verified(
        client,
        db_session,
        merchant.slug,
        program["slug"],
        {
            "email": "primera-tostadora@example.com",
            "display_name": "Primera Clienta",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    login(client, OWNER_EMAIL)

    final = client.get(url).json()
    assert final == {
        "program_ready": True,
        "store_ready": True,
        "qr_ready": True,
        "first_member": True,
        "completed": True,
    }
