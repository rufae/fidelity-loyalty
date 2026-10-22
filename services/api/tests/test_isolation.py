"""Pruebas de aislamiento multiempresa (AGENTS.md §8.2) — FASE 2.

Son las pruebas negativas obligatorias: un usuario del comercio A intentando
leer, modificar o administrar datos del comercio B debe recibir la misma
respuesta que si el comercio no existiera (404), sin que se filtre su
existencia.
"""

import uuid

from app.domain.roles import MerchantRole, PlatformRole
from app.models.audit import AuditEvent
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_B_EMAIL,
    OWNER_EMAIL,
    PLATFORM_EMAIL,
    STAFF_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    login,
)


def _setup_two_merchants(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    """Comercio A (owner + staff) y comercio B (owner distinto)."""
    owner_a = create_user(db_session, OWNER_EMAIL, display_name="Owner A")
    staff_a = create_user(db_session, STAFF_EMAIL, display_name="Staff A")
    owner_b = create_user(db_session, OWNER_B_EMAIL, display_name="Owner B")
    merchant_a = create_merchant_with_owner(db_session, owner_a, name="Cafetería A")
    create_merchant_with_owner(db_session, owner_b, name="Cafetería B")
    add_member(db_session, staff_a, merchant_a, MerchantRole.STAFF)
    db_session.commit()
    assert merchant_a.id is not None and owner_b.id is not None
    return merchant_a.id, owner_b.id


def test_plataforma_crea_comercio_y_genera_slug(client: TestClient, db_session: Session) -> None:
    create_user(db_session, PLATFORM_EMAIL, platform_role=PlatformRole.OWNER)
    db_session.commit()
    login(client, PLATFORM_EMAIL)

    response = client.post(
        "/api/v1/platform/merchants",
        json={
            "name": "Panadería El Horno",
            "owner_email": "horno@example.com",
            "owner_password": "panaderia-larga-1234",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["slug"] == "panaderia-el-horno"
    assert payload["status"] == "active"


def test_nombres_repetidos_generan_slugs_distintos(client: TestClient, db_session: Session) -> None:
    create_user(db_session, PLATFORM_EMAIL, platform_role=PlatformRole.OWNER)
    db_session.commit()
    login(client, PLATFORM_EMAIL)
    body = {
        "name": "Cafetería Central",
        "owner_email": "x@example.com",
        "owner_password": "larga-12345678",
    }
    first = client.post("/api/v1/platform/merchants", json=body)
    second = client.post(
        "/api/v1/platform/merchants",
        json={**body, "owner_email": "y@example.com"},
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["slug"] != second.json()["slug"]


def test_un_comercio_ajeno_responde_404_como_si_no_existiera(
    client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _setup_two_merchants(db_session)
    login(client, OWNER_B_EMAIL)

    ajeno = client.get(f"/api/v1/merchants/{merchant_a}")
    inexistente = client.get("/api/v1/merchants/00000000-0000-0000-0000-000000000000")

    assert ajeno.status_code == inexistente.status_code == 404
    assert ajeno.json() == inexistente.json()


def test_no_se_puede_administrar_el_equipo_de_otro_comercio(
    client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _setup_two_merchants(db_session)
    login(client, OWNER_B_EMAIL)

    lectura = client.get(f"/api/v1/merchants/{merchant_a}/users")
    alta = client.post(
        f"/api/v1/merchants/{merchant_a}/users",
        json={"email": "intruso@example.com", "password": "intruso-larga-123", "role": "admin"},
    )

    assert lectura.status_code == 404
    assert alta.status_code == 404


def test_staff_no_administra_el_equipo_de_su_propio_comercio(
    client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _setup_two_merchants(db_session)
    login(client, STAFF_EMAIL)

    assert client.get(f"/api/v1/merchants/{merchant_a}").status_code == 200  # lectura: sí
    assert client.get(f"/api/v1/merchants/{merchant_a}/users").status_code == 404  # gestión: no
    assert (
        client.patch(f"/api/v1/merchants/{merchant_a}", json={"name": "Hackeado"}).status_code
        == 404
    )


def test_el_listado_solo_muestra_tus_comercios(client: TestClient, db_session: Session) -> None:
    _setup_two_merchants(db_session)
    login(client, OWNER_EMAIL)

    response = client.get("/api/v1/merchants")

    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert names == ["Cafetería A"]


def test_un_admin_no_puede_crear_otro_owner(client: TestClient, db_session: Session) -> None:
    from app.models.merchant import Merchant

    merchant_a, _ = _setup_two_merchants(db_session)
    merchant = db_session.get(Merchant, merchant_a)
    assert merchant is not None
    admin_user = create_user(db_session, "admin-a@example.com", display_name="Admin A")
    add_member(db_session, admin_user, merchant, MerchantRole.ADMIN)
    db_session.commit()

    login(client, "admin-a@example.com")
    response = client.post(
        f"/api/v1/merchants/{merchant_a}/users",
        json={"email": "nuevo@example.com", "password": "nuevo-largo-1234", "role": "owner"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "merchant_access_denied"


def test_no_se_puede_degradar_al_ultimo_owner(client: TestClient, db_session: Session) -> None:
    merchant_a, _ = _setup_two_merchants(db_session)
    login(client, OWNER_EMAIL)

    from app.models.user import User

    owner_user = db_session.query(User).filter(User.email == OWNER_EMAIL).one()
    response = client.patch(
        f"/api/v1/merchants/{merchant_a}/users/{owner_user.id}",
        json={"role": "viewer"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_alta_de_usuario_y_cambio_de_rollo_funcionan_en_tu_comercio(
    client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _setup_two_merchants(db_session)
    login(client, OWNER_EMAIL)

    alta = client.post(
        f"/api/v1/merchants/{merchant_a}/users",
        json={"email": "nuevo@example.com", "password": "nuevo-largo-1234", "role": "staff"},
    )
    assert alta.status_code == 201, alta.text
    user_id = alta.json()["user_id"]

    cambio = client.patch(f"/api/v1/merchants/{merchant_a}/users/{user_id}", json={"role": "admin"})
    assert cambio.status_code == 200
    assert cambio.json()["role"] == "admin"


def test_un_usuario_de_un_comercio_no_ve_las_acciones_de_otro(
    client: TestClient, db_session: Session
) -> None:
    """La auditoría de un comercio no debe poder leerse desde otro (§8.4)."""
    merchant_a, _ = _setup_two_merchants(db_session)
    login(client, OWNER_B_EMAIL)
    events = db_session.query(AuditEvent).filter(AuditEvent.merchant_id == merchant_a).all()
    assert events == []  # los eventos existen solo si se registraron acciones


def test_sin_sesion_no_se_lee_nada(client: TestClient) -> None:
    assert client.get("/api/v1/merchants").status_code == 401
    assert client.get("/api/v1/platform/merchants").status_code == 401
    assert client.get("/api/v1/merchants/00000000-0000-0000-0000-000000000000").status_code == 401


def test_plataforma_puede_gestionar_cualquier_comercio(
    client: TestClient, db_session: Session
) -> None:
    """§8.1: el rol de plataforma administra todos los comercios.

    Regresión de un fallo real: la UI mostraba los comercios al administrador
    pero cada endpoint de comercio le devolvía 404.
    """
    from app.domain.roles import PlatformRole

    merchant_a, _ = _setup_two_merchants(db_session)
    create_user(db_session, PLATFORM_EMAIL, platform_role=PlatformRole.OWNER)
    db_session.commit()
    login(client, PLATFORM_EMAIL)

    lectura = client.get(f"/api/v1/merchants/{merchant_a}")
    programas = client.get(f"/api/v1/merchants/{merchant_a}/programs")
    miembros = client.get(f"/api/v1/merchants/{merchant_a}/members")

    assert lectura.status_code == 200
    assert programas.status_code == 200
    assert miembros.status_code == 200
    # Y el listado global le muestra todos los comercios.
    assert len(client.get("/api/v1/merchants").json()) == 2
